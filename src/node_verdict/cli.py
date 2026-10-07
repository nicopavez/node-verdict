"""Command line: demo, verdicts, simulate."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .attribution import AttributionConfig
from .engine import run_engine
from .policy import PolicyConfig, plan
from .report import action_table, comparison_table, sensitivity_table, verdict_table
from .scenario import BAD_NODE, DEFAULT_SPARES, SDC_NODE, build_scenario
from .simulator import SimParams, compare, sensitivity


def _conditions(scenario, no_history: bool):
    history = scenario.history.only_jobs(scenario.job_ids()) if no_history else None
    return run_engine(scenario, AttributionConfig(), history)


def cmd_verdicts(args) -> None:
    scenario = build_scenario(args.spares)
    conditions = _conditions(scenario, args.no_history)
    if args.json:
        print(json.dumps([c.to_dict() for c in conditions], indent=2))
        return
    print(verdict_table(conditions))
    silent = len(scenario.pool) - len({c.node for c in conditions})
    print(f"\n{len(conditions)} nodes have a verdict. {silent} nodes have none (no condition is not the same as healthy).")


def cmd_simulate(args) -> None:
    scenario = build_scenario(args.spares)
    params = SimParams(ckpt_interval_steps=args.ckpt, restart_steps=args.restart, act_at=args.act_at)
    print(comparison_table(compare(scenario, params), scenario))
    if args.sensitivity:
        print("\nGoodput gain of attributed repair, in percentage points:\n")
        print(sensitivity_table(sensitivity(scenario, restart_steps=args.restart)))


def cmd_demo(args) -> None:
    scenario = build_scenario(args.spares)
    conditions = _conditions(scenario, no_history=False)
    sizes = {j.id: len(j.nodes) for j in scenario.jobs}
    actions = plan(conditions, len(scenario.pool), scenario.spares, sizes, PolicyConfig())

    print(f"Node Verdict {__version__}: 32-node pool, {scenario.spares} spares, 3 jobs")
    print("Timing is real (ByteDance sample traces). Node history and anomaly events are synthetic.\n")

    print("1. Verdicts\n")
    print(verdict_table(conditions))
    found = {c.node: c.reason.value for c in conditions}
    ok_lemon = found.get(BAD_NODE) == "NodeLemon"
    ok_sdc = found.get(SDC_NODE) == "SDCSuspect"
    cleared = [c for c in conditions if c.reason.value == "WorkloadImbalance" and c.node in scenario.truth]
    print(f"\nPlanted bad node {BAD_NODE}: {'found' if ok_lemon else 'MISSED'}. "
          f"Planted corrupting chip {SDC_NODE}: {'found' if ok_sdc else 'MISSED'}. "
          f"Planted nodes wrongly cleared: {len(cleared)}.")

    print("\n2. Actions\n")
    print(action_table(actions))

    print("\n3. Naive replace-any-slow-node vs attributed repair\n")
    print(comparison_table(compare(scenario, SimParams(ckpt_interval_steps=args.ckpt, restart_steps=args.restart)), scenario))
    print(f"\nAssumed, not measured: repair acts after 20% of the run, checkpoint every {args.ckpt} steps, "
          f"restart costs {args.restart} steps.")

    print("\n4. How much of the goodput gain is attribution, and how much is just waiting for a checkpoint\n")
    print(sensitivity_table(sensitivity(scenario, restart_steps=args.restart)))
    print("\nThe counts (healthy nodes replaced, spares used, chip pulled) do not depend on these assumptions.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="node-verdict", description="Is the slowdown the node or the job?")
    parser.add_argument("--spares", type=int, default=DEFAULT_SPARES, help="spare nodes in the pool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("demo", help="run the full demo")
    p.add_argument("--ckpt", type=int, default=100)
    p.add_argument("--restart", type=int, default=10)
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("verdicts", help="print verdicts")
    p.add_argument("--json", action="store_true", help="emit node conditions as JSON")
    p.add_argument("--no-history", action="store_true", help="use only the current jobs, no earlier history")
    p.set_defaults(func=cmd_verdicts)

    p = sub.add_parser("simulate", help="compare naive and attributed repair")
    p.add_argument("--ckpt", type=int, default=100)
    p.add_argument("--restart", type=int, default=10)
    p.add_argument("--act-at", type=float, default=0.20)
    p.add_argument("--sensitivity", action="store_true")
    p.set_defaults(func=cmd_simulate)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
