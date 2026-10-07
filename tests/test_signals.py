import pandas as pd
import pytest

from node_verdict.signals import compute_signals


def make_table(stage_compute, steps=10, outlier=None):
    """stage_compute: {stage: seconds}. Two data-parallel replicas per stage."""
    rows = []
    rank = 0
    for stage, secs in stage_compute.items():
        for dp in range(2):
            for step in range(steps):
                t = secs * (outlier[1] if outlier == (rank, outlier[1]) else 1.0) if outlier else secs
                rows.append(dict(step=step, rank=rank, stage=stage, dp_rank=dp, compute_s=t, fb_corr=0.5))
            rank += 1
    return pd.DataFrame(rows)


def test_one_slow_rank_stands_out_from_its_stage_peers():
    df = make_table({0: 10.0, 1: 10.0}, outlier=(1, 2.0))
    sig = compute_signals(df, "j")
    assert sig.ranks[1].rel_median == pytest.approx(1.33, abs=0.01)  # vs median of two replicas
    assert sig.ranks[1].persistence == 1.0
    assert sig.ranks[0].persistence == 0.0


def test_a_slow_stage_does_not_make_any_rank_a_peer_outlier():
    df = make_table({0: 10.0, 1: 10.0, 2: 10.0, 3: 20.0})
    sig = compute_signals(df, "j")
    assert all(s.persistence == 0.0 for s in sig.ranks.values())
    assert sig.stage_ratio[3] == pytest.approx(2.0)
    assert sig.stage_ratio[0] == pytest.approx(1.0)


def test_missing_columns_fail_loudly():
    with pytest.raises(ValueError, match="missing columns"):
        compute_signals(pd.DataFrame({"step": [1]}), "j")


def test_empty_table_fails_loudly():
    cols = ["step", "rank", "stage", "dp_rank", "compute_s", "fb_corr"]
    with pytest.raises(ValueError, match="empty"):
        compute_signals(pd.DataFrame(columns=cols), "j")
