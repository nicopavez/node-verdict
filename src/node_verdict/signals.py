"""Turn a job's per-rank, per-step compute times into attribution signals.

The key move is the comparison group. A rank is compared to its stage peers
(the same pipeline stage in other data-parallel replicas), not to the whole
job. Stages do different amounts of work, so a whole-job comparison blames
healthy nodes for how the job was split.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("step", "rank", "stage", "dp_rank", "compute_s", "fb_corr")


@dataclass(frozen=True)
class RankSignal:
    rank: int
    stage: int
    dp_rank: int
    mean_compute_s: float
    rel_median: float  # median over steps of compute / stage-peer median
    persistence: float  # share of steps where rel >= peer_threshold
    step_cv: float  # std / mean of compute across steps


@dataclass(frozen=True)
class JobSignals:
    job_id: str
    n_steps: int
    ranks: dict[int, RankSignal]
    stage_ratio: dict[int, float]  # stage median compute / job median compute
    fb_corr: float  # median forward vs backward correlation across micro-batches
    step_cv: float  # median over ranks of step-to-step variation
    job_median_compute_s: float


def compute_signals(table: pd.DataFrame, job_id: str, peer_threshold: float = 1.15) -> JobSignals:
    missing = [c for c in REQUIRED_COLUMNS if c not in table.columns]
    if missing:
        raise ValueError(f"trace table is missing columns: {missing}")
    if table.empty:
        raise ValueError("trace table is empty")

    per = table.copy()
    peer_median = per.groupby(["step", "stage"])["compute_s"].transform("median")
    per["rel"] = per["compute_s"] / peer_median

    ranks: dict[int, RankSignal] = {}
    for rank, g in per.groupby("rank"):
        mean = float(g["compute_s"].mean())
        ranks[int(rank)] = RankSignal(
            rank=int(rank),
            stage=int(g["stage"].iloc[0]),
            dp_rank=int(g["dp_rank"].iloc[0]),
            mean_compute_s=mean,
            rel_median=float(g["rel"].median()),
            persistence=float((g["rel"] >= peer_threshold).mean()),
            step_cv=float(g["compute_s"].std(ddof=0) / mean) if mean > 0 else 0.0,
        )

    means = pd.Series({r: s.mean_compute_s for r, s in ranks.items()})
    job_median = float(means.median())
    stage_of = {r: s.stage for r, s in ranks.items()}
    stage_medians = means.groupby(pd.Series(stage_of)).median()
    stage_ratio = {int(s): float(m / job_median) for s, m in stage_medians.items()}

    return JobSignals(
        job_id=job_id,
        n_steps=int(per["step"].nunique()),
        ranks=ranks,
        stage_ratio=stage_ratio,
        fb_corr=float(np.nanmedian(per["fb_corr"])),
        step_cv=float(np.median([s.step_cv for s in ranks.values()])),
        job_median_compute_s=job_median,
    )
