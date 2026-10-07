# Derived data

Small tables derived from ByteDance's published sample traces. See `NOTICE` at the repo root for the source and license.

| File | What it is |
|---|---|
| `AR_rank_steps.csv`, `ST_rank_steps.csv`, `SE_rank_steps.csv` | One row per rank per step: forward, backward and total compute seconds, and the forward-versus-backward correlation across micro-batches |
| `AR_whatif.json`, `ST_whatif.json`, `SE_whatif.json` | Mean step time, ideal step time, overall slowdown, and slowdown split by data-parallel rank and by stage, trimmed from the published what-if results |

Trace names follow the ByteDance artifact. `AR` is an artificially slowed worker. `ST` is stage partitioning imbalance. `SE` is sequence length imbalance. `SE` keeps 8 of its 64 ranks.

Rebuild with:

```bash
git clone https://github.com/ByteDance-Seed/StragglerAnalysis /tmp/StragglerAnalysis
pip install -e ".[prepare]"
python scripts/prepare_traces.py --src /tmp/StragglerAnalysis --out data/derived
```
