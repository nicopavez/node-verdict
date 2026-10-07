"""The public contract: node conditions with stable reason codes.

Reason codes are an API. Customers write automation against them, so renaming
one or changing its meaning is a breaking change. `REASON_CODES_V1` is frozen
and a test fails if it moves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

API_VERSION = "nodeverdict.dev/v1alpha1"
CONDITION_TYPE = "NodeVerdict"


class ReasonCode(str, Enum):
    NODE_LEMON = "NodeLemon"
    NODE_SUSPECT = "NodeSuspect"
    SDC_SUSPECT = "SDCSuspect"
    WORKLOAD_IMBALANCE = "WorkloadImbalance"


REASON_CODES_V1 = frozenset({"NodeLemon", "NodeSuspect", "SDCSuspect", "WorkloadImbalance"})

# Who owns the fix. A workload verdict never changes a node.
ATTRIBUTED_TO = {
    ReasonCode.NODE_LEMON: "node",
    ReasonCode.NODE_SUSPECT: "node",
    ReasonCode.SDC_SUSPECT: "node",
    ReasonCode.WORKLOAD_IMBALANCE: "job",
}


@dataclass(frozen=True)
class Evidence:
    signal: str
    value: str
    note: str = ""

    def to_dict(self) -> dict:
        out = {"signal": self.signal, "value": self.value}
        if self.note:
            out["note"] = self.note
        return out


@dataclass(frozen=True)
class NodeCondition:
    """A Kubernetes-style condition for one node, scoped to one job.

    `confidence` is an ordinal band (low, medium, high), not a probability.
    """

    node: str
    job: str
    reason: ReasonCode
    message: str
    confidence: str
    last_transition_time: str
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)

    @property
    def attributed_to(self) -> str:
        return ATTRIBUTED_TO[self.reason]

    def to_dict(self) -> dict:
        return {
            "apiVersion": API_VERSION,
            "node": self.node,
            "job": self.job,
            "condition": {
                "type": CONDITION_TYPE,
                "status": "True",
                "reason": self.reason.value,
                "message": self.message,
                "lastTransitionTime": self.last_transition_time,
                "attributedTo": self.attributed_to,
                "confidence": self.confidence,
                "evidence": [e.to_dict() for e in self.evidence],
            },
        }
