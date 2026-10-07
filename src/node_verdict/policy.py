"""Policy: what to do with a verdict. Rules and guards, all editable config.

Attribution says whose fault it is. Policy decides the action. Keeping them
apart means an operator can change an action without touching the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .conditions import NodeCondition, ReasonCode

REPLACE = "ReplaceAtCheckpoint"
QUARANTINE = "QuarantineForRetest"
WATCH = "Watch"
INFORM = "InformCustomer"

NODE_CHANGING = {REPLACE, QUARANTINE}

DEFAULT_ACTIONS = {
    ReasonCode.NODE_LEMON: REPLACE,
    ReasonCode.SDC_SUSPECT: QUARANTINE,
    ReasonCode.NODE_SUSPECT: WATCH,
    ReasonCode.WORKLOAD_IMBALANCE: INFORM,
}


@dataclass(frozen=True)
class PolicyConfig:
    actions: dict[ReasonCode, str] = field(default_factory=lambda: dict(DEFAULT_ACTIONS))
    # Never change more than this share of the pool at once (the EKS 20% lesson).
    max_concurrent_fraction: float = 0.20
    # If this share of a job's nodes would change at once, treat it as a correlated event.
    correlation_fraction: float = 0.50


@dataclass(frozen=True)
class Action:
    node: str
    job: str
    kind: str
    reason: ReasonCode
    status: str  # planned, blocked_no_spare, held_correlated, capped
    detail: str

    @property
    def changes_node(self) -> bool:
        return self.kind in NODE_CHANGING and self.status == "planned"


def plan(
    conditions: list[NodeCondition],
    pool_size: int,
    spares: int,
    nodes_per_job: dict[str, int],
    cfg: PolicyConfig = PolicyConfig(),
) -> list[Action]:
    wanted = [(c, cfg.actions[c.reason]) for c in conditions]

    # Correlation guard: many nodes failing together points at something shared.
    held_jobs: set[str] = set()
    for job, size in nodes_per_job.items():
        changing = sum(1 for c, k in wanted if c.job == job and k in NODE_CHANGING)
        if size and changing / size >= cfg.correlation_fraction:
            held_jobs.add(job)

    cap = max(1, int(cfg.max_concurrent_fraction * pool_size))
    used = 0
    spares_left = spares
    actions: list[Action] = []
    for cond, kind in wanted:
        if kind in NODE_CHANGING:
            if cond.job in held_jobs:
                actions.append(Action(cond.node, cond.job, WATCH, cond.reason, "held_correlated",
                                      "Many nodes in this job flagged at once. Automation halted for review."))
                continue
            if used >= cap:
                actions.append(Action(cond.node, cond.job, kind, cond.reason, "capped",
                                      f"Fleet safety limit of {cap} concurrent node changes reached."))
                continue
            if spares_left <= 0:
                actions.append(Action(cond.node, cond.job, kind, cond.reason, "blocked_no_spare",
                                      "No spare node available."))
                continue
            used += 1
            spares_left -= 1
            actions.append(Action(cond.node, cond.job, kind, cond.reason, "planned", _detail(kind)))
        else:
            actions.append(Action(cond.node, cond.job, kind, cond.reason, "planned", _detail(kind)))
    return actions


def _detail(kind: str) -> str:
    return {
        REPLACE: "Replace at the next checkpoint boundary. No mid-step restart.",
        QUARANTINE: "Pull from the pool and retest under realistic load before it returns.",
        WATCH: "No node change. Keep collecting evidence.",
        INFORM: "No node change. Tell the customer the slowdown is in the job setup.",
    }[kind]
