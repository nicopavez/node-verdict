"""Compare two repair policies on the demo pool.

Naive: flag any rank that runs slower than the job's median rank, replace the
worst first until the spares run out. It cannot see silent data corruption.

Attributed: run the verdict engine, then the policy. Only node verdicts change
nodes, and they change them at a checkpoint boundary.

Real inputs: per-rank timing and ByteDance's published what-if slowdowns.
Assumed inputs (SimParams): when the policy acts, the checkpoint interval and
the restart cost. Change them and the goodput numbers move. The counts of
healthy nodes replaced and spares used do not depend on them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .attribution import AttributionConfig
from .engine import run_engine
from .policy import NODE_CHANGING, QUARANTINE, REPLACE, PolicyConfig, plan
from .scenario import Scenario


@dataclass(frozen=True)
class SimParams:
    horizon_steps: int = 1000  # steps of ideal work per job
    act_at: float = 0.20  # share of the horizon that has run before repair acts
    ckpt_interval_steps: int = 100  # steps between checkpoints
    restart_steps: int = 10  # cost of one restart, in ideal steps
    naive_threshold: float = 1.15  # rank mean compute vs job median


@dataclass
class PolicyResult:
    name: str
    replaced: list[str] = field(default_factory=list)
    quarantined: list[str] = field(default_factory=list)
    healthy_replaced: list[str] = field(default_factory=list)
    bad_node_fixed: bool = False
    sdc_pulled: bool = False
    spares_used: int = 0
    flagged_unserved: int = 0
    jobs_told_not_node: list[str] = field(default_factory=list)
    goodput_by_job: dict[str, float] = field(default_factory=dict)
    goodput: float = 0.0


def _naive_flags(scenario: Scenario, threshold: float) -> list[tuple[float, str, str]]:
    """(ratio, job id, node) for every rank above threshold, worst first."""
    flags = []
    for job in scenario.jobs:
        med = job.signals.job_median_compute_s
        for rank, sig in job.signals.ranks.items():
            ratio = sig.mean_compute_s / med
            if ratio >= threshold:
                flags.append((ratio, job.id, job.node_of_rank[rank]))
    return sorted(flags, reverse=True)


def _s_before(job) -> float:
    return float(job.whatif["blocking_slowdown"])


def _s_after_node_fix(job, culprit_node: str) -> float:
    """Slowdown left once the culprit's node is replaced, from the published what-if."""
    by_dp = job.whatif["blocking_decompose_by_dp_rank"]
    rank = next(r for r, n in job.node_of_rank.items() if n == culprit_node)
    dp = str(job.signals.ranks[rank].dp_rank)
    rest = [v for k, v in by_dp.items() if k != dp]
    return max(rest) if rest else 1.0


def _job_goodput(job, params: SimParams, fixed_node: str | None, restarted: bool, at_checkpoint: bool) -> float:
    """Ideal time over actual time for one job. 1.0 means no slowdown and no lost work."""
    h = params.horizon_steps
    s0 = _s_before(job)
    if fixed_node is not None and job.cause == "node":
        s1 = _s_after_node_fix(job, fixed_node)
        run = params.act_at * h * s0 + (1 - params.act_at) * h * s1
    else:
        run = h * s0  # replacing hardware does not change a workload problem
    loss = 0.0
    if restarted:
        lost_steps = params.restart_steps + (0 if at_checkpoint else params.ckpt_interval_steps / 2)
        loss = lost_steps * s0
    return h / (run + loss)


def _finish(result: PolicyResult, scenario: Scenario, params: SimParams, changed: dict[str, list[str]], at_ckpt: bool) -> PolicyResult:
    total_nodes = sum(len(j.nodes) for j in scenario.jobs)
    weighted = 0.0
    for job in scenario.jobs:
        nodes = changed.get(job.id, [])
        fixed = next((n for n in nodes if scenario.truth.get(n) == "bad_node"), None)
        g = _job_goodput(job, params, fixed, restarted=bool(nodes), at_checkpoint=at_ckpt)
        result.goodput_by_job[job.id] = g
        weighted += g * len(job.nodes)
    result.goodput = weighted / total_nodes
    for n in result.replaced + result.quarantined:
        if scenario.truth.get(n) is None:
            result.healthy_replaced.append(n)
    result.bad_node_fixed = any(scenario.truth.get(n) == "bad_node" for n in result.replaced + result.quarantined)
    result.sdc_pulled = any(scenario.truth.get(n) == "sdc" for n in result.replaced + result.quarantined)
    result.spares_used = len(result.replaced) + len(result.quarantined)
    return result


def simulate_naive(scenario: Scenario, params: SimParams = SimParams(), at_checkpoint: bool = False) -> PolicyResult:
    """Replace any slow rank. With at_checkpoint, it waits for a checkpoint like the attributed policy."""
    result = PolicyResult("naive+checkpoint" if at_checkpoint else "naive")
    flags = _naive_flags(scenario, params.naive_threshold)
    changed: dict[str, list[str]] = {}
    spares = scenario.spares
    for _, job_id, node in flags:
        if spares > 0:
            spares -= 1
            result.replaced.append(node)
            changed.setdefault(job_id, []).append(node)
        else:
            result.flagged_unserved += 1
    return _finish(result, scenario, params, changed, at_ckpt=at_checkpoint)


def simulate_attributed(
    scenario: Scenario,
    params: SimParams = SimParams(),
    cfg: AttributionConfig = AttributionConfig(),
    policy_cfg: PolicyConfig = PolicyConfig(),
) -> PolicyResult:
    result = PolicyResult("attributed")
    conditions = run_engine(scenario, cfg)
    sizes = {j.id: len(j.nodes) for j in scenario.jobs}
    actions = plan(conditions, len(scenario.pool), scenario.spares, sizes, policy_cfg)
    changed: dict[str, list[str]] = {}
    for a in actions:
        if a.kind in NODE_CHANGING and a.status == "planned":
            (result.replaced if a.kind == REPLACE else result.quarantined).append(a.node)
            changed.setdefault(a.job, []).append(a.node)
        elif a.kind in NODE_CHANGING:
            result.flagged_unserved += 1
        elif a.kind == "InformCustomer" and a.job not in result.jobs_told_not_node:
            result.jobs_told_not_node.append(a.job)
    return _finish(result, scenario, params, changed, at_ckpt=True)


def compare(scenario: Scenario, params: SimParams = SimParams()) -> list[PolicyResult]:
    """Three policies. The middle one separates timing from attribution.

    naive: replace any slow rank, mid-run.
    naive+checkpoint: the same flags, but wait for a checkpoint. Any policy can do this.
    attributed: verdict engine plus policy. Also waits for a checkpoint.
    """
    return [
        simulate_naive(scenario, params),
        simulate_naive(scenario, params, at_checkpoint=True),
        simulate_attributed(scenario, params),
    ]


def sensitivity(scenario: Scenario, ckpts=(50, 100, 200), restart_steps: int = 10) -> list[tuple[int, float, float]]:
    """(checkpoint interval, total gain, gain from attribution alone), in percentage points.

    Total is attributed vs naive. Attribution alone is attributed vs naive+checkpoint.
    """
    rows = []
    for c in ckpts:
        naive, naive_ckpt, attributed = compare(
            scenario, SimParams(ckpt_interval_steps=c, restart_steps=restart_steps)
        )
        rows.append((c, 100 * (attributed.goodput - naive.goodput), 100 * (attributed.goodput - naive_ckpt.goodput)))
    return rows
