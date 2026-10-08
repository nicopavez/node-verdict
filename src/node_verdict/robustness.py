"""Threshold robustness: how far can each threshold move before a verdict changes?

The thresholds were set by hand on three traces, and the public artifact has
no held-out data to validate them. This is the next best check. Sweep each
threshold on its own, keep the rest at their defaults, and report the band
where every verdict matches the default run, plus what changes just outside.

A wide band says the demo is not balanced on a knife edge. It does not say the
thresholds are right for a real fleet. The planted slow worker runs 2.35x its
peers, far above any sensible threshold. A degraded node in production may run
1.1x.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .attribution import AttributionConfig
from .engine import run_engine
from .scenario import Scenario, build_scenario

# The peer threshold also decides persistence and the history written for the
# current jobs, so changing it means rebuilding the scenario.
REBUILD = {"peer_threshold"}

GRIDS: dict[str, list[float]] = {
    "peer_threshold": [round(1.02 + 0.02 * i, 2) for i in range(75)],  # 1.02 to 2.50
    "persistence_min": [round(0.05 * i, 2) for i in range(1, 21)],  # 0.05 to 1.00
    "stage_threshold": [round(1.00 + 0.02 * i, 2) for i in range(41)],  # 1.00 to 1.80
    "lemon_min_score": [float(x) for x in range(1, 13)],
    "lemon_min_jobs": [float(x) for x in range(1, 7)],
    "sdc_min_jobs": [float(x) for x in range(1, 7)],
}

INT_PARAMS = {"lemon_min_jobs", "sdc_min_jobs"}

# What each threshold is tested against. Bands on synthetic history only show
# that the planted history is not borderline. They say nothing about real fleets.
BASIS = {
    "peer_threshold": "real timing",
    "persistence_min": "real timing",
    "stage_threshold": "real timing",
    "lemon_min_score": "synthetic history",
    "lemon_min_jobs": "synthetic history",
    "sdc_min_jobs": "synthetic history",
}

NODE_CHANGING_REASONS = {"NodeLemon", "SDCSuspect"}


@dataclass(frozen=True)
class Band:
    param: str
    default: float
    low: float  # lowest grid value with the same verdicts as the default, contiguous with it
    high: float
    grid_min: float
    grid_max: float
    below: str  # what changes just under the band, or "" if the band reaches the grid edge
    above: str

    @property
    def basis(self) -> str:
        return BASIS[self.param]

    def fmt(self, x: float) -> str:
        return f"{x:g}" if self.param in INT_PARAMS or self.param == "lemon_min_score" else f"{x:.2f}"


def verdicts(scenario: Scenario, cfg: AttributionConfig) -> dict[str, str]:
    return {c.node: c.reason.value for c in run_engine(scenario, cfg)}


def _cfg(param: str, value: float, base: AttributionConfig) -> AttributionConfig:
    return replace(base, **{param: int(value) if param in INT_PARAMS else value})


def _nodes(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{names[0]} to {names[-1]}" if len(names) > 2 else " and ".join(names)


def _describe(ref: dict[str, str], got: dict[str, str]) -> str:
    """Plain words for how a verdict map differs from the default, with nodes grouped by change."""
    changes: dict[str, list[str]] = {}
    for node in sorted(set(ref) | set(got)):
        a, b = ref.get(node), got.get(node)
        if a == b:
            continue
        if a is None:
            what = ("gain", b)
        elif b is None:
            what = ("lose", a)
        else:
            what = ("", f"{a} to {b}")
        changes.setdefault(what, []).append(node)

    def phrase(verb: str, rest: str, n: int) -> str:
        return f"{verb}{'s' if verb and n == 1 else ''} {rest}".strip()

    return "; ".join(f"{_nodes(nodes)} {phrase(v, r, len(nodes))}" for (v, r), nodes in changes.items())


def sweep(param: str, values: list[float], base: AttributionConfig = AttributionConfig()) -> list[tuple[float, dict[str, str]]]:
    scenario = None if param in REBUILD else build_scenario(cfg=base)
    out = []
    for v in values:
        cfg = _cfg(param, v, base)
        s = build_scenario(cfg=cfg) if param in REBUILD else scenario
        out.append((v, verdicts(s, cfg)))
    return out


def band(param: str, values: list[float] | None = None, base: AttributionConfig = AttributionConfig()) -> Band:
    values = values if values is not None else GRIDS[param]
    default = float(getattr(base, param))
    ref = verdicts(build_scenario(cfg=base), base)
    rows = sweep(param, values, base)
    same = [v == ref for _, v in rows]

    # Start from the grid point nearest the default and grow outward while verdicts match.
    start = min(range(len(rows)), key=lambda i: abs(rows[i][0] - default))
    if not same[start]:
        raise ValueError(f"{param}: the grid point nearest the default does not reproduce the default verdicts")
    lo = start
    while lo > 0 and same[lo - 1]:
        lo -= 1
    hi = start
    while hi < len(rows) - 1 and same[hi + 1]:
        hi += 1

    below = _describe(ref, rows[lo - 1][1]) if lo > 0 else ""
    above = _describe(ref, rows[hi + 1][1]) if hi < len(rows) - 1 else ""
    return Band(param, default, rows[lo][0], rows[hi][0], values[0], values[-1], below, above)


def all_bands(base: AttributionConfig = AttributionConfig()) -> list[Band]:
    return [band(p, base=base) for p in GRIDS]


def healthy_nodes_ever_changed(base: AttributionConfig = AttributionConfig()) -> dict[str, list[tuple[float, str]]]:
    """For every grid point of every threshold: healthy nodes that would get a node-changing verdict.

    Empty lists mean no threshold setting on the grid would replace or pull a healthy node.
    """
    truth = build_scenario(cfg=base).truth
    out: dict[str, list[tuple[float, str]]] = {}
    for param, values in GRIDS.items():
        out[param] = [
            (v, node)
            for v, got in sweep(param, values, base)
            for node, reason in got.items()
            if reason in NODE_CHANGING_REASONS and node not in truth
        ]
    return out
