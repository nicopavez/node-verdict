# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Read `HANDOFF.md` first for the full context, the known weaknesses, and the definition of done.

## What this is

A product design project about the data plane of a GPU cloud. Node Verdict decides whether a GPU training slowdown is the node's fault or the job's fault, before anything gets replaced. It is a verdict engine, a policy layer and a simulator, run on real ByteDance sample traces plus labeled synthetic node history. It defines behavior. It does not operate hardware.

## Commands

```bash
pip install -e ".[dev]"
pytest -q
python -m node_verdict demo
python -m node_verdict verdicts            # add --json, or --no-history
python -m node_verdict simulate --sensitivity
python -m node_verdict robustness         # threshold sweep

# Rebuild data/derived/ from ByteDance's artifact (needs pyarrow)
git clone https://github.com/ByteDance-Seed/StragglerAnalysis <somewhere>
pip install -e ".[prepare]"
python scripts/prepare_traces.py --src <somewhere> --out data/derived
```

Python 3.11 or newer. No network is needed to run the demo or the tests.

## Architecture

Evidence goes in, a verdict comes out, policy turns the verdict into an action.

- `signals.py`: per-rank signals. Each rank is compared to its **stage peers** (same pipeline stage, other data-parallel replicas), never to the whole job.
- `history.py`: per-node history across jobs. This is the cloud-only signal.
- `attribution.py`: deterministic rules in a fixed order, first match wins. No model.
- `conditions.py`: Kubernetes-style node conditions. The four reason codes are a pinned API.
- `policy.py`: actions are editable config. A fleet cap and a correlation guard sit on top.
- `scenario.py`: the 32-node demo. Real timing, synthetic node history.
- `robustness.py`: sweeps each threshold and reports where verdicts change.
- `simulator.py`: compares naive, naive+checkpoint, peer-aware, and attributed repair.

Things that are easy to get wrong:

- **Absent is not healthy.** A node with no matching rule gets no condition. Do not add a "Healthy" verdict.
- **Reason codes are a contract.** `tests/test_conditions.py` pins `NodeLemon`, `NodeSuspect`, `SDCSuspect`, `WorkloadImbalance`. A rename needs a new API version, not a quiet edit.
- **A workload verdict never changes a node.** `ATTRIBUTED_TO` in `conditions.py` and the action map in `policy.py` enforce it.
- **Keep the `naive+checkpoint` and `peer-aware` controls.** Most of the goodput gain is checkpoint timing and stage-peer comparison, which a good detector can do. Attribution scores slightly below peer-aware on goodput. Removing either control would overstate what attribution adds.
- **Counts do not depend on assumed parameters.** Healthy nodes replaced, spares used and the chip caught are independent of checkpoint interval and restart cost. Goodput is not. Keep that distinction in anything you write.
- **Do not tune thresholds to the three traces.** An earlier rule was deleted because tuning it would have been overfitting. Add robustness checks instead.
- **Real vs synthetic.** Real: per-rank compute time and the what-if slowdowns from ByteDance's traces. Synthetic: rank-to-node mapping, node history, the anomaly stream. Say which, every time.
- **Trace SE is trimmed** to the first four data-parallel replicas of each stage (8 of 64 ranks) so the pool is 32 nodes. Its what-if numbers describe the full job.

## Conventions

- **No em dashes anywhere** (code, docs, comments, commit messages). `tests/test_repo_hygiene.py` fails on one. Short, plain, declarative sentences. First person for proposals.
- No LLM calls in this repo. Rules decide.
- Public sources only. No proprietary company material and no interview prep files (gitignored).
- Free to run and free to host. No paid APIs.
- Do not push to a remote without asking.
- Commit subjects are short and imperative.
