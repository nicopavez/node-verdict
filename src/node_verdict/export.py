"""Export everything the web demo shows as one JSON document.

The web app renders this file and decides nothing. Every verdict, action,
policy result and robustness band comes from the same Python that the tests
cover. `tests/test_export.py` fails if the committed JSON drifts from a fresh
export, so the demo cannot quietly disagree with the engine.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .attribution import AttributionConfig
from .conditions import API_VERSION, ATTRIBUTED_TO, REASON_CODES_V1, ReasonCode
from .engine import run_engine
from .policy import DEFAULT_ACTIONS, PolicyConfig, plan
from .robustness import all_bands, healthy_nodes_ever_changed
from .scenario import BAD_NODE, DECOY_NODE, SDC_NODE, Scenario, build_scenario
from .simulator import SimParams, compare, owner_by_job, sensitivity

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "web" / "src" / "data" / "node-verdict-data.json"

TRACE_LABELS = {
    "AR": "One worker artificially slowed, a stand-in for a bad node",
    "ST": "Uneven pipeline stage partitioning",
    "SE": "Uneven sequence lengths",
}

REASON_TEXT = {
    "NodeLemon": "Slow against stage peers in most steps, and the node was the outlier in other jobs too.",
    "NodeSuspect": "Slow against stage peers in most steps, but only this job is on record.",
    "SDCSuspect": "Training anomalies in two or more jobs while idle checks pass and timing is normal.",
    "WorkloadImbalance": "The whole pipeline stage is slow and this rank matches its stage peers.",
}


def _r(x: float, n: int = 4) -> float:
    return round(float(x), n)


def _job(job) -> dict:
    sig = job.signals
    table = job.table.sort_values(["rank", "step"])
    steps = sorted(int(s) for s in table["step"].unique())
    meta = job.whatif.get("job_meta", {})
    ranks = []
    for rank in sorted(sig.ranks):
        s = sig.ranks[rank]
        rows = table[table["rank"] == rank]
        ranks.append({
            "rank": rank,
            "node": job.node_of_rank[rank],
            "stage": s.stage,
            "dp": s.dp_rank,
            "meanComputeS": _r(s.mean_compute_s),
            "vsJobMedian": _r(s.mean_compute_s / sig.job_median_compute_s, 3),
            "peerRatio": _r(s.rel_median, 3),
            "persistence": _r(s.persistence, 3),
            "computeS": [_r(x) for x in rows["compute_s"]],
        })
    return {
        "id": job.id,
        "trace": job.trace,
        "traceLabel": TRACE_LABELS[job.trace],
        "cause": job.cause,
        "nodes": job.nodes,
        "steps": steps,
        "stages": sorted({r["stage"] for r in ranks}),
        "dps": sorted({r["dp"] for r in ranks}),
        "stageRatio": {str(k): _r(v, 3) for k, v in sorted(sig.stage_ratio.items())},
        "fbCorr": _r(sig.fb_corr, 3),
        "stepCv": _r(sig.step_cv, 3),
        "jobMedianComputeS": _r(sig.job_median_compute_s),
        "slowdown": _r(job.whatif["blocking_slowdown"], 3),
        "fullJob": {k: meta.get(k) for k in ("dp_size", "pp_size", "tp_size", "world_size")},
        "ranks": ranks,
    }


def _verdicts(scenario: Scenario, history=None) -> list[dict]:
    conditions = run_engine(scenario, AttributionConfig(), history)
    sizes = {j.id: len(j.nodes) for j in scenario.jobs}
    actions = plan(conditions, len(scenario.pool), scenario.spares, sizes, PolicyConfig())
    out = []
    for c, a in zip(conditions, actions):
        d = c.to_dict()
        d["action"] = {"kind": a.kind, "status": a.status, "detail": a.detail, "changesNode": a.changes_node}
        out.append(d)
    return out


def _history(scenario: Scenario) -> dict:
    current = scenario.job_ids()
    out = {}
    for name in scenario.history.names():
        h = scenario.history.get(name)
        rate = h.active_check_pass_rate()
        out[name] = {
            "elevatedJobs": h.elevated_jobs(),
            "anomalyJobs": h.anomaly_jobs(),
            "lemonScore": _r(h.lemon_score(), 2),
            "activeCheckPassRate": None if rate is None else _r(rate, 2),
            "observations": [
                {
                    "job": o.job_id,
                    "current": o.job_id in current,
                    "persistentOutlier": o.persistent_outlier,
                    "peerRatio": o.peer_ratio,
                    "anomalyEvents": o.anomaly_events,
                    "excludedByJob": o.excluded_by_job,
                    "repairTickets": o.repair_tickets,
                    "multiNodeFailure": o.multi_node_failure,
                    "activeCheckPassed": o.active_check_passed,
                }
                for o in h.observations
            ],
        }
    return out


def _policy(r) -> dict:
    return {
        "name": r.name,
        "replaced": r.replaced,
        "quarantined": r.quarantined,
        "healthyReplaced": r.healthy_replaced,
        "sparesUsed": r.spares_used,
        "flaggedUnserved": r.flagged_unserved,
        "badNodeFixed": r.bad_node_fixed,
        "sdcPulled": r.sdc_pulled,
        "ownerByJob": r.owner_by_job,
        "jobsRightOwner": r.jobs_right_owner,
        "goodput": _r(r.goodput),
        "goodputByJob": {k: _r(v) for k, v in r.goodput_by_job.items()},
    }


def build_export() -> dict:
    scenario = build_scenario()
    params = SimParams()
    cfg = AttributionConfig()
    no_history = scenario.history.only_jobs(scenario.job_ids())
    bands = all_bands()
    changed = healthy_nodes_ever_changed()
    return {
        "meta": {
            "version": __version__,
            "apiVersion": API_VERSION,
            "asOf": scenario.as_of,
            "poolSize": len(scenario.pool),
            "spares": scenario.spares,
            "real": [
                "Per-rank compute time per step for three jobs (ByteDance sample traces, Apache-2.0)",
                "Per-job slowdown from ByteDance's published what-if analysis",
                "What actually caused each job's slowdown (the trace labels)",
            ],
            "synthetic": [
                "Which node each trace rank runs on",
                "Each node's history across earlier jobs",
                "Training anomaly events that stand in for silent data corruption",
            ],
            "planted": {"badNode": BAD_NODE, "sdcNode": SDC_NODE, "decoyNode": DECOY_NODE},
        },
        "config": {k: v for k, v in asdict(cfg).items() if k != "weights"} | {"lemonWeights": asdict(cfg.weights)},
        "simParams": asdict(params),
        "reasonCodes": [
            {
                "code": code,
                "attributedTo": ATTRIBUTED_TO[ReasonCode(code)],
                "defaultAction": DEFAULT_ACTIONS[ReasonCode(code)],
                "when": REASON_TEXT[code],
            }
            for code in ("NodeLemon", "SDCSuspect", "NodeSuspect", "WorkloadImbalance")
            if code in REASON_CODES_V1
        ],
        "pool": scenario.pool,
        "jobs": [_job(j) for j in scenario.jobs],
        "verdicts": {"withHistory": _verdicts(scenario), "noHistory": _verdicts(scenario, no_history)},
        "ownerByJob": {
            "withHistory": owner_by_job(run_engine(scenario, cfg)),
            "noHistory": owner_by_job(run_engine(scenario, cfg, no_history)),
        },
        "history": _history(scenario),
        "policies": [_policy(r) for r in compare(scenario, params)],
        "sensitivity": [
            {"ckptSteps": c, "vsNaive": _r(a, 2), "vsNaiveCheckpoint": _r(b, 2), "vsPeerAware": _r(p, 2)}
            for c, a, b, p in sensitivity(scenario, restart_steps=params.restart_steps)
        ],
        "robustness": {
            "bands": [asdict(b) | {"basis": b.basis} for b in bands],
            "healthyNodesEverChanged": sum(len(v) for v in changed.values()),
        },
    }


def dumps(data: dict) -> str:
    return json.dumps(data, indent=1, sort_keys=False) + "\n"


def write(out: Path = DEFAULT_OUT) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dumps(build_export()), encoding="utf-8", newline="\n")
    return out
