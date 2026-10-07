"""Per-node history across jobs.

This is the part only the cloud can see. A customer sees one job. The cloud
sees every job a node has served. A slowdown that follows one node across
different jobs is the node. One that follows a stage inside one job is the job.

The signal types follow what Meta reports using for lemon detection: jobs that
excluded a node, repair tickets, and multi-node failures a node caused. The
weights below are illustrative defaults, not Meta's model.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NodeObservation:
    job_id: str
    persistent_outlier: bool = False  # slow vs stage peers in most steps of that job
    peer_ratio: float | None = None
    anomaly_events: int = 0  # loss spikes or gradient-norm outliers attributed to the node
    excluded_by_job: bool = False  # a customer job asked to avoid this node
    repair_tickets: int = 0
    multi_node_failure: bool = False
    active_check_passed: bool | None = None  # None means no check ran, which is not a pass


@dataclass(frozen=True)
class LemonWeights:
    elevated_job: float = 1.0
    excluded_by_job: float = 1.0
    repair_ticket: float = 0.75
    multi_node_failure: float = 1.5


@dataclass
class NodeHistory:
    node: str
    observations: list[NodeObservation] = field(default_factory=list)

    def add(self, obs: NodeObservation) -> None:
        self.observations.append(obs)

    def elevated_jobs(self) -> int:
        return len({o.job_id for o in self.observations if o.persistent_outlier})

    def anomaly_jobs(self) -> int:
        return len({o.job_id for o in self.observations if o.anomaly_events > 0})

    def lemon_score(self, w: LemonWeights = LemonWeights()) -> float:
        return (
            w.elevated_job * self.elevated_jobs()
            + w.excluded_by_job * sum(o.excluded_by_job for o in self.observations)
            + w.repair_ticket * sum(o.repair_tickets for o in self.observations)
            + w.multi_node_failure * sum(o.multi_node_failure for o in self.observations)
        )

    def active_check_pass_rate(self) -> float | None:
        ran = [o.active_check_passed for o in self.observations if o.active_check_passed is not None]
        if not ran:
            return None
        return sum(ran) / len(ran)


class HistoryStore:
    """A plain in-memory store. A real one would be a table keyed by node."""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeHistory] = {}

    def node(self, name: str) -> NodeHistory:
        return self._nodes.setdefault(name, NodeHistory(name))

    def get(self, name: str) -> NodeHistory | None:
        return self._nodes.get(name)

    def add(self, name: str, obs: NodeObservation) -> None:
        self.node(name).add(obs)

    def only_jobs(self, job_ids: set[str]) -> "HistoryStore":
        """A copy keeping only the given jobs. Used to show a verdict with no prior history."""
        out = HistoryStore()
        for name, h in self._nodes.items():
            for o in h.observations:
                if o.job_id in job_ids:
                    out.add(name, o)
        return out

    def names(self) -> list[str]:
        return sorted(self._nodes)
