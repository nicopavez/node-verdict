from node_verdict.scenario import build_scenario
from node_verdict.simulator import SimParams, compare, sensitivity, simulate_attributed, simulate_naive


def test_attributed_replaces_no_healthy_node(scenario):
    r = simulate_attributed(scenario)
    assert r.healthy_replaced == []
    assert r.replaced == ["N00"] and r.quarantined == ["N27"]
    assert r.bad_node_fixed and r.sdc_pulled


def test_naive_wastes_spares_on_healthy_nodes_and_misses_the_chip(scenario):
    r = simulate_naive(scenario)
    assert len(r.healthy_replaced) == 3
    assert r.bad_node_fixed
    assert not r.sdc_pulled
    assert r.spares_used == scenario.spares
    assert r.flagged_unserved == 3


def test_attributed_leaves_spares_in_the_pool(scenario):
    assert simulate_attributed(scenario).spares_used < simulate_naive(scenario).spares_used


def test_waiting_for_a_checkpoint_explains_most_of_the_goodput_gain(scenario):
    naive, naive_ckpt, attributed = compare(scenario)
    total = attributed.goodput - naive.goodput
    from_attribution = attributed.goodput - naive_ckpt.goodput
    assert total > 0
    assert 0 <= from_attribution < total / 5  # attribution alone is the small part


def test_counts_do_not_depend_on_assumed_parameters(scenario):
    a = compare(scenario, SimParams(ckpt_interval_steps=50, restart_steps=5))
    b = compare(scenario, SimParams(ckpt_interval_steps=200, restart_steps=20))
    for x, y in zip(a, b):
        assert (x.healthy_replaced, x.spares_used, x.sdc_pulled) == (y.healthy_replaced, y.spares_used, y.sdc_pulled)


def test_sensitivity_gain_grows_with_checkpoint_interval(scenario):
    rows = sensitivity(scenario)
    totals = [t for _, t, _ in rows]
    assert totals == sorted(totals)


def test_workload_slowdown_is_not_fixed_by_replacing_nodes(scenario):
    naive = simulate_naive(scenario)
    job_b = scenario.job("job-b")
    s = float(job_b.whatif["blocking_slowdown"])
    # replaced nodes in job-b, yet goodput stays below 1 / slowdown because of lost work
    assert naive.goodput_by_job["job-b"] < 1 / s


def test_fewer_spares_changes_who_gets_served():
    tight = build_scenario(spares=1)
    r = simulate_naive(tight)
    assert r.spares_used == 1 and r.bad_node_fixed  # worst-first reaches the real bad node
    assert r.flagged_unserved == 6


def test_missing_data_gives_a_clear_error(monkeypatch, tmp_path):
    import pytest

    monkeypatch.setenv("NODE_VERDICT_DATA", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="NODE_VERDICT_DATA"):
        build_scenario()
