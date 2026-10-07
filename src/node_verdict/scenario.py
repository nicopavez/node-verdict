"""The 32-node demo pool: three jobs on real traces, plus labeled synthetic history.

What is real: per-rank compute times from ByteDance's published sample traces
(three jobs) and their published what-if slowdown results.

What is synthetic, and labeled as such everywhere it is used:
  * the mapping from trace ranks to node names,
  * each node's history across earlier jobs,
  * the training anomaly stream that stands in for silent data corruption.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .attribution import AttributionConfig, is_timing_outlier
from .history import HistoryStore, NodeObservation
from .signals import JobSignals, compute_signals

AS_OF = "2026-10-06T00:00:00Z"
POOL_SIZE = 32
DEFAULT_SPARES = 4

# (job id, trace name, what actually causes the slowdown)
JOB_SPECS = [
    ("job-a", "AR", "node"),  # one artificially slowed worker, a stand-in for a bad node
    ("job-b", "ST", "workload"),  # uneven pipeline stage partitioning
    ("job-c", "SE", "workload"),  # uneven sequence lengths
]

BAD_NODE = "N00"  # hosts the slowed worker of job-a
SDC_NODE = "N27"  # planted corrupting chip, hosted by job-c
DECOY_NODE = "N20"  # one old blip in one job, in job-b


def data_dir() -> Path:
    env = os.environ.get("NODE_VERDICT_DATA")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "data" / "derived"


@dataclass
class Job:
    id: str
    trace: str
    cause: str  # ground truth: "node" or "workload"
    table: pd.DataFrame
    whatif: dict
    node_of_rank: dict[int, str]
    signals: JobSignals | None = None

    @property
    def nodes(self) -> list[str]:
        return [self.node_of_rank[r] for r in sorted(self.node_of_rank)]


@dataclass
class Scenario:
    pool: list[str]
    jobs: list[Job]
    history: HistoryStore
    truth: dict[str, str] = field(default_factory=dict)  # node -> "bad_node" | "sdc"
    spares: int = DEFAULT_SPARES
    as_of: str = AS_OF

    def job(self, job_id: str) -> Job:
        return next(j for j in self.jobs if j.id == job_id)

    def job_ids(self) -> set[str]:
        return {j.id for j in self.jobs}


def _prior_history(seed: int = 7) -> HistoryStore:
    """Earlier jobs for every node. Synthetic, deterministic, and mostly clean."""
    rng = random.Random(seed)
    store = HistoryStore()
    planted = {BAD_NODE, SDC_NODE, DECOY_NODE}
    for i in range(POOL_SIZE):
        node = f"N{i:02d}"
        if node in planted:
            continue
        for k in range(rng.randint(3, 6)):
            store.add(
                node,
                NodeObservation(
                    job_id=f"prior-{k + 1:02d}",
                    peer_ratio=round(rng.uniform(0.97, 1.04), 3),
                    active_check_passed=True,
                ),
            )

    # A lemon: slow in four different jobs, avoided by two, ticketed twice, took down
    # a multi-node job once, and it passes every idle check.
    for job, ratio, excluded, tickets, multi in [
        ("prior-01", 2.31, True, 0, False),
        ("prior-02", 2.18, False, 1, False),
        ("prior-03", 2.40, True, 0, True),
        ("prior-04", 2.05, False, 1, False),
    ]:
        store.add(
            BAD_NODE,
            NodeObservation(job, True, ratio, excluded_by_job=excluded, repair_tickets=tickets,
                            multi_node_failure=multi, active_check_passed=True),
        )

    # A corrupting chip: normal timing, passes checks, anomalies in three earlier jobs.
    for job, events in [("prior-01", 0), ("prior-02", 3), ("prior-03", 2), ("prior-04", 4)]:
        store.add(SDC_NODE, NodeObservation(job, False, 1.0, anomaly_events=events, active_check_passed=True))

    # A decoy: one elevated reading in one old job. Not enough to call it a lemon.
    for job, ratio, elevated in [("prior-01", 1.02, False), ("prior-02", 1.21, True), ("prior-03", 1.0, False)]:
        store.add(DECOY_NODE, NodeObservation(job, elevated, ratio, active_check_passed=True))
    return store


def build_scenario(spares: int = DEFAULT_SPARES, cfg: AttributionConfig = AttributionConfig()) -> Scenario:
    base = data_dir()
    if not (base / "AR_rank_steps.csv").exists():
        raise FileNotFoundError(
            f"Derived trace tables not found in {base}. Run from a source checkout "
            "(pip install -e .) or set NODE_VERDICT_DATA to the data/derived directory."
        )
    pool = [f"N{i:02d}" for i in range(POOL_SIZE)]
    history = _prior_history()

    jobs: list[Job] = []
    next_node = 0
    for job_id, trace, cause in JOB_SPECS:
        table = pd.read_csv(base / f"{trace}_rank_steps.csv")
        whatif = json.loads((base / f"{trace}_whatif.json").read_text())
        ranks = sorted(table["rank"].unique())
        node_of_rank = {int(r): f"N{next_node + i:02d}" for i, r in enumerate(ranks)}
        next_node += len(ranks)
        job = Job(job_id, trace, cause, table, whatif, node_of_rank)
        job.signals = compute_signals(table, job_id, cfg.peer_threshold)
        jobs.append(job)
    if next_node != POOL_SIZE:
        raise ValueError(f"demo jobs use {next_node} nodes, expected {POOL_SIZE}")

    # Add what each node did in the jobs running now.
    for job in jobs:
        for rank, node in job.node_of_rank.items():
            sig = job.signals.ranks[rank]
            history.add(
                node,
                NodeObservation(
                    job_id=job.id,
                    persistent_outlier=is_timing_outlier(sig, cfg),
                    peer_ratio=round(sig.rel_median, 3),
                    anomaly_events=2 if node == SDC_NODE else 0,
                    active_check_passed=True,
                ),
            )

    truth = {BAD_NODE: "bad_node", SDC_NODE: "sdc"}
    return Scenario(pool=pool, jobs=jobs, history=history, truth=truth, spares=spares)
