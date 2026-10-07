"""Turn ByteDance's published sample traces into small derived tables.

Input: a clone of https://github.com/ByteDance-Seed/StragglerAnalysis (Apache-2.0).
Output: per-rank, per-step compute tables and a trimmed copy of the published
what-if results, so this repo runs offline without the 9 MB of raw traces.

Usage:
    python scripts/prepare_traces.py --src /path/to/StragglerAnalysis --out data/derived

Needs pandas, numpy and pyarrow (pip install -e ".[prepare]").
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

COMPUTE = ("forward-compute", "backward-compute")

# Trace name -> optional filter. The SE job has 64 ranks. Only the first 4
# data-parallel replicas of each pipeline stage are kept (8 ranks) so the demo
# pool stays at 32 nodes. The what-if numbers below still describe the full job.
FILTERS = {
    "AR": None,
    "ST": None,
    "SE": lambda df: df[df["dp_rank"] < 4],
}

WHATIF_KEYS = (
    "blocking_slowdown",
    "blocking_decompose_by_dp_rank",
    "blocking_decompose_by_stage",
)


def fb_corr(group: pd.DataFrame) -> float:
    """Correlation of forward vs backward time across micro-batches."""
    fwd = group[group["optype"] == COMPUTE[0]].set_index("mb_id")["duration"]
    bwd = group[group["optype"] == COMPUTE[1]].set_index("mb_id")["duration"]
    joined = pd.concat([fwd.rename("f"), bwd.rename("b")], axis=1).dropna()
    if len(joined) < 3 or joined["f"].std() == 0 or joined["b"].std() == 0:
        return float("nan")
    return float(np.corrcoef(joined["f"], joined["b"])[0, 1])


def derive(trace_path: Path, keep) -> pd.DataFrame:
    df = pd.read_parquet(trace_path)
    if keep is not None:
        df = keep(df)
    comp = df[df["optype"].isin(COMPUTE)]
    keys = ["step", "rank", "stage", "dp_rank"]
    sums = (
        comp.pivot_table(index=keys, columns="optype", values="duration", aggfunc="sum")
        .rename(columns={COMPUTE[0]: "fwd_s", COMPUTE[1]: "bwd_s"})
        .reset_index()
    )
    sums["compute_s"] = sums["fwd_s"] + sums["bwd_s"]
    corr = (
        comp.groupby(keys)
        .apply(fb_corr, include_groups=False)
        .rename("fb_corr")
        .reset_index()
    )
    out = sums.merge(corr, on=keys)
    cols = ["step", "rank", "stage", "dp_rank", "compute_s", "fwd_s", "bwd_s", "fb_corr"]
    return out[cols].sort_values(["step", "rank"]).round(6)


def trim_whatif(result_path: Path) -> dict:
    full = json.loads(result_path.read_text())
    trimmed = {"job_meta": full["job_meta"]}
    base = list(full["step_t_base"].values())
    ideal = list(full["step_t_noblk"].values())
    trimmed["mean_step_time_s"] = round(float(np.mean(base)), 4)
    trimmed["mean_ideal_step_time_s"] = round(float(np.mean(ideal)), 4)
    for key in WHATIF_KEYS:
        trimmed[key] = full[key]
    return trimmed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, keep in FILTERS.items():
        table = derive(args.src / "data" / f"trace-{name}.parquet", keep)
        table.to_csv(args.out / f"{name}_rank_steps.csv", index=False)
        whatif = trim_whatif(args.src / "data" / f"result-{name}.json")
        (args.out / f"{name}_whatif.json").write_text(json.dumps(whatif, indent=2) + "\n")
        print(f"{name}: {len(table)} rank-step rows, {table['rank'].nunique()} ranks")


if __name__ == "__main__":
    main()
