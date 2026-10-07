"""Run the engine over every job in a scenario."""
from __future__ import annotations

from .attribution import AttributionConfig, attribute
from .conditions import NodeCondition
from .history import HistoryStore
from .scenario import Scenario


def run_engine(
    scenario: Scenario,
    cfg: AttributionConfig = AttributionConfig(),
    history: HistoryStore | None = None,
) -> list[NodeCondition]:
    """Return conditions for every job. Pass `history` to override the scenario's."""
    store = history if history is not None else scenario.history
    out: list[NodeCondition] = []
    for job in scenario.jobs:
        out.extend(attribute(job.signals, job.node_of_rank, store, scenario.as_of, cfg))
    return out
