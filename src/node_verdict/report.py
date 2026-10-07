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

    n_jobs = len(scenario.jobs)
    rows = [
        row("Healthy nodes replaced", lambda r: str(len(r.healthy_replaced))),
        row(f"Spares used (of {scenario.spares})", lambda r: str(r.spares_used)),
        row("Flagged nodes left unserved", lambda r: str(r.flagged_unserved)),
        row("Bad node fixed", lambda r: yes(r.bad_node_fixed)),
        row("Corrupting chip pulled", lambda r: yes(r.sdc_pulled)),
        row(f"Slow jobs given the right owner (of {n_jobs})", lambda r: str(len(r.jobs_right_owner))),
        row("Goodput, node-weighted (assumed model)", lambda r: pct(r.goodput)),
        *[row(f"  {j.id}", lambda r, j=j: pct(r.goodput_by_job[j.id])) for j in scenario.jobs],
    ]
    return table(["metric"] + [r.name for r in results], rows)


def robustness_table(bands) -> str:
    rows = [
        [b.param, b.fmt(b.default), f"{b.fmt(b.low)} to {b.fmt(b.high)}", f"{b.fmt(b.grid_min)} to {b.fmt(b.grid_max)}", b.basis]
        for b in bands
    ]
    return table(["threshold", "default", "verdicts unchanged", "range tested", "tested against"], rows)


def robustness_edges(bands) -> str:
    lines = []
    for b in bands:
        if b.below:
            lines.append(f"{b.param} below {b.fmt(b.low)}: {b.below}.")
        if b.above:
            lines.append(f"{b.param} above {b.fmt(b.high)}: {b.above}.")
    return "\n".join(lines)


def sensitivity_table(rows: list[tuple[int, float, float, float]]) -> str:
    body = [[f"every {c} steps", f"{a:+.1f} pts", f"{b:+.1f} pts", f"{c2:+.1f} pts"] for c, a, b, c2 in rows]
    return table(["checkpoint interval", "vs naive", "vs naive+checkpoint", "vs peer-aware"], body)
