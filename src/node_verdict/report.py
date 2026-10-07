"""Plain-text tables for the CLI. No dependencies."""
from __future__ import annotations

from .conditions import NodeCondition
from .policy import Action
from .scenario import Scenario
from .simulator import PolicyResult


def table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)] if rows else [len(h) for h in headers]
    line = lambda cells: "  ".join(str(c).ljust(w) for c, w in zip(cells, widths)).rstrip()
    out = [line(headers), line(["-" * w for w in widths])]
    out.extend(line(r) for r in rows)
    return "\n".join(out)


def verdict_table(conditions: list[NodeCondition]) -> str:
    rows = [[c.job, c.node, c.reason.value, c.attributed_to, c.confidence, c.message] for c in conditions]
    return table(["job", "node", "verdict", "owner", "confidence", "why"], rows)


def action_table(actions: list[Action]) -> str:
    rows = [[a.job, a.node, a.kind, a.status, a.detail] for a in actions]
    return table(["job", "node", "action", "status", "detail"], rows)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def comparison_table(results: list[PolicyResult], scenario: Scenario) -> str:
    def yes(b: bool) -> str:
        return "yes" if b else "no"

    def row(label: str, fn) -> list[str]:
        return [label] + [fn(r) for r in results]

    rows = [
        row("Goodput (node-weighted)", lambda r: pct(r.goodput)),
        *[row(f"  {j.id}", lambda r, j=j: pct(r.goodput_by_job[j.id])) for j in scenario.jobs],
        row("Healthy nodes replaced", lambda r: str(len(r.healthy_replaced))),
        row("Bad node fixed", lambda r: yes(r.bad_node_fixed)),
        row("Corrupting chip pulled", lambda r: yes(r.sdc_pulled)),
        row(f"Spares used (of {scenario.spares})", lambda r: str(r.spares_used)),
        row("Flagged nodes left unserved", lambda r: str(r.flagged_unserved)),
        row("Jobs told it is not the node", lambda r: str(len(r.jobs_told_not_node))),
    ]
    return table(["metric"] + [r.name for r in results], rows)


def sensitivity_table(rows: list[tuple[int, float, float]]) -> str:
    body = [[f"every {c} steps", f"{total:+.1f} pts", f"{attr:+.1f} pts"] for c, total, attr in rows]
    return table(["checkpoint interval", "total gain vs naive", "from attribution alone"], body)
