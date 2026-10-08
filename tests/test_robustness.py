import pytest

from node_verdict.robustness import band, healthy_nodes_ever_changed


@pytest.fixture(scope="module")
def stage():
    return band("stage_threshold")


def test_default_stage_threshold_sits_inside_its_stable_band(stage):
    assert stage.low <= 1.15 <= stage.high
    assert (stage.low, stage.high) == (1.06, 1.20)


def test_stage_threshold_fails_safe_on_both_sides(stage):
    # Too low: job-a's healthy stage 3 (1.04x the job median) gets blamed on the job.
    assert "N12 to N15 gain WorkloadImbalance" in stage.below
    # Too high: job-c's slow stage (1.20x) is no longer explained. It gets no condition, not a node fault.
    assert "N28 to N31 lose WorkloadImbalance" in stage.above


def test_peer_threshold_covers_the_range_the_handoff_asked_for():
    b = band("peer_threshold")
    assert b.low <= 1.10 and b.high >= 1.25
    assert b.above == "N00 loses NodeLemon"  # only once the threshold passes the planted 2.35x


def test_persistence_requirement_does_not_move_any_verdict():
    b = band("persistence_min")
    assert (b.low, b.high) == (b.grid_min, b.grid_max)


def test_no_threshold_setting_replaces_or_pulls_a_healthy_node():
    changed = healthy_nodes_ever_changed()
    assert all(v == [] for v in changed.values()), changed


def test_band_rejects_a_grid_that_misses_the_default():
    with pytest.raises(ValueError, match="nearest the default"):
        band("stage_threshold", values=[1.60, 1.70])
