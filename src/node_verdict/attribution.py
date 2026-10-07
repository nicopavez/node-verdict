"""The verdict engine. Deterministic rules, no model in the decision path.

Order matters. The first rule that fires wins for a node:

1. SDCSuspect: the node keeps producing training anomalies across jobs, passes
   its idle checks, and shows no timing problem. Slowness cannot explain wrong
   answers, so this runs first.
2. Persistent outlier: the rank is slow against its stage peers in most steps.
   With history across jobs it is NodeLemon. With only this job it is
   NodeSuspect, because one job cannot separate a bad node from a bad position.
3. Stage slow: the whole stage is slow and the rank is normal for its stage.
   The slowdown follows the stage, so it is WorkloadImbalance.

Uneven sequence lengths show up as a job-level signature: forward and backward
times move together and vary step to step. That signature only adds a note to a
stage verdict. It does not flag single ranks, because a rank that is slow in a
handful of steps is inside the noise.

A node with none of these gets no condition. Absent is not healthy.
"""
from __future__ import annotations

from dataclasses import dataclass

from .conditions import Evidence, NodeCondition, ReasonCode
from .history import HistoryStore, LemonWeights
from .signals import JobSignals


@dataclass(frozen=True)
class AttributionConfig:
    peer_threshold: float = 1.15  # rank vs stage peers
    persistence_min: float = 0.8  # share of steps that must exceed the threshold
    stage_threshold: float = 1.15  # stage median vs job median
    skew_corr: float = 0.9  # forward vs backward time correlation
    skew_cv: float = 0.03  # step-to-step variation across the job
    lemon_min_jobs: int = 2  # distinct jobs where the node was an outlier
    lemon_min_score: float = 4.0
    lemon_high_score: float = 8.0
    sdc_min_jobs: int = 2
    sdc_high_jobs: int = 3
    sdc_check_pass_min: float = 0.95
    weights: LemonWeights = LemonWeights()


def _fmt(x: float) -> str:
    return f"{x:.2f}"


def is_timing_outlier(sig, cfg: AttributionConfig = AttributionConfig()) -> bool:
    """Slow against stage peers in most steps."""
    return sig.rel_median >= cfg.peer_threshold and sig.persistence >= cfg.persistence_min


def attribute(
    signals: JobSignals,
    node_of_rank: dict[int, str],
    history: HistoryStore,
    as_of: str,
    cfg: AttributionConfig = AttributionConfig(),
) -> list[NodeCondition]:
    """Return one condition per node that has a verdict. Nodes without one are omitted."""
    out: list[NodeCondition] = []
    skew = signals.fb_corr >= cfg.skew_corr and signals.step_cv >= cfg.skew_cv

    for rank in sorted(signals.ranks):
        sig = signals.ranks[rank]
        node = node_of_rank[rank]
        hist = history.get(node)
        job = signals.job_id

        def make(reason: ReasonCode, message: str, confidence: str, evidence: list[Evidence]) -> NodeCondition:
            return NodeCondition(node, job, reason, message, confidence, as_of, tuple(evidence))

        timing_outlier = is_timing_outlier(sig, cfg)

        # 1. Silent data corruption: anomalies across jobs, passes checks, normal timing.
        if hist is not None and not timing_outlier:
            rate = hist.active_check_pass_rate()
            if (
                hist.anomaly_jobs() >= cfg.sdc_min_jobs
                and rate is not None
                and rate >= cfg.sdc_check_pass_min
            ):
                conf = "high" if hist.anomaly_jobs() >= cfg.sdc_high_jobs else "medium"
                out.append(
                    make(
                        ReasonCode.SDC_SUSPECT,
                        "Training anomalies follow this node across jobs while idle checks pass.",
                        conf,
                        [
                            Evidence("anomaly_jobs", str(hist.anomaly_jobs()), "distinct jobs with loss or gradient anomalies"),
                            Evidence("active_check_pass_rate", _fmt(rate), "idle-node checks passed, so they do not explain it"),
                            Evidence("peer_ratio", _fmt(sig.rel_median), "timing is normal, so this is not a straggler"),
                        ],
                    )
                )
                continue

        # 2. Persistent outlier against stage peers.
        if timing_outlier:
            elevated = hist.elevated_jobs() if hist is not None else 1
            score = hist.lemon_score(cfg.weights) if hist is not None else cfg.weights.elevated_job
            base = [
                Evidence("peer_ratio", _fmt(sig.rel_median), "median compute vs same-stage peers"),
                Evidence("persistence", _fmt(sig.persistence), "share of steps above threshold"),
            ]
            if elevated >= cfg.lemon_min_jobs and score >= cfg.lemon_min_score:
                conf = "high" if score >= cfg.lemon_high_score else "medium"
                out.append(
                    make(
                        ReasonCode.NODE_LEMON,
                        "Slowdown follows this node across different jobs.",
                        conf,
                        base
                        + [
                            Evidence("elevated_jobs", str(elevated), "distinct jobs where it was the outlier"),
                            Evidence("lemon_score", _fmt(score), "weighted history signals"),
                        ],
                    )
                )
            else:
                out.append(
                    make(
                        ReasonCode.NODE_SUSPECT,
                        "Slow against its peers in this job. One job cannot separate the node from its position.",
                        "low",
                        base + [Evidence("elevated_jobs", str(elevated), "needs a second job to confirm")],
                    )
                )
            continue

        # 3. The whole stage is slow and this rank is normal for its stage.
        ratio = signals.stage_ratio[sig.stage]
        if ratio >= cfg.stage_threshold:
            conf = "high" if ratio / cfg.stage_threshold >= 1.4 else "medium"
            causes = "stage partitioning"
            if skew:
                causes += " and uneven sequence lengths"
            out.append(
                make(
                    ReasonCode.WORKLOAD_IMBALANCE,
                    f"Slowdown follows pipeline stage {sig.stage}, not this node ({causes}).",
                    conf,
                    [
                        Evidence("stage_ratio", _fmt(ratio), f"stage {sig.stage} median compute vs job median"),
                        Evidence("peer_ratio", _fmt(sig.rel_median), "this rank matches its stage peers"),
                    ],
                )
            )
            continue

    return out
