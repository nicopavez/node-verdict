"""Command line: demo, verdicts, simulate."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .attribution import AttributionConfig
from .engine import run_engine
from .policy import PolicyConfig, plan
from .report import (
    action_table,
    comparison_table,
    robustness_edges,
    robustness_table,
    sensitivity_table,
    verdict_table,
)
from .robustness import all_bands, healthy_nodes_ever_changed
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


def cmd_robustness(args) -> None:
    bands = all_bands()
    print("Each threshold swept on its own, the rest at defaults. A band is where every verdict matches the default run.\n")
    print(robustness_table(bands))
    print("\nJust outside each band:\n")
    print(robustness_edges(bands))
    changed = healthy_nodes_ever_changed()
    worst = sum(len(v) for v in changed.values())
    print(f"\nHealthy nodes that would be replaced or pulled at any setting tested: {worst}.")
    print("\nA wide band means the demo is not on a knife edge. It does not validate the thresholds for a real fleet.")
    print("The planted slow worker runs 2.35x its peers, so any peer threshold below that catches it. "
          "Bands on synthetic history only show the planted history is not borderline.")


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

    print("\n3. Four repair policies on the same pool\n")
    print("naive: replace any rank slower than the job median, mid-run.")
    print("naive+checkpoint: the same, but wait for a checkpoint. Any policy can do this.")
    print("peer-aware: replace a rank persistently slow against its stage peers, at a checkpoint. The fair baseline.")
    print("attributed: verdict engine plus policy.\n")
    print(comparison_table(compare(scenario, SimParams(ckpt_interval_steps=args.ckpt, restart_steps=args.restart)), scenario))
    print("\nThe counts do not depend on any assumption. Goodput does: repair acts after 20% of the run, "
          f"checkpoint every {args.ckpt} steps, restart costs {args.restart} steps.")

    print("\n4. Where the goodput gain comes from, in percentage points\n")
    print(sensitivity_table(sensitivity(scenario, restart_steps=args.restart)))
    print("\nNearly all of it is checkpoint timing and comparing to stage peers. Attribution adds the chip, "
          "an owner for every slow job, and no replacement on one job of evidence. Pulling the chip costs a "
          "restart, and this model does not price corrupted training, so attribution scores slightly below peer-aware.")


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

    p = sub.add_parser("robustness", help="sweep each threshold and show where verdicts change")
    p.set_defaults(func=cmd_robustness)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
