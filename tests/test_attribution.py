from node_verdict.attribution import attribute
from node_verdict.engine import run_engine
from node_verdict.scenario import BAD_NODE, DECOY_NODE, SDC_NODE


def by_node(conditions):
    return {c.node: c for c in conditions}


def test_bad_node_is_a_lemon_with_history(scenario):
    c = by_node(run_engine(scenario))[BAD_NODE]
    assert c.reason.value == "NodeLemon"
    assert c.confidence == "high"
    assert c.attributed_to == "node"


def test_bad_node_is_only_a_suspect_without_history(scenario):
    only_now = scenario.history.only_jobs(scenario.job_ids())
    c = by_node(run_engine(scenario, history=only_now))[BAD_NODE]
    assert c.reason.value == "NodeSuspect"  # one job cannot separate node from position
    assert c.confidence == "low"


def test_stage_imbalance_is_blamed_on_the_job_not_the_nodes(scenario):
    conds = [c for c in run_engine(scenario) if c.job == "job-b"]
    assert {c.node for c in conds} == {"N22", "N23"}  # only the slow stage, 2 of 8 nodes
    assert all(c.reason.value == "WorkloadImbalance" and c.attributed_to == "job" for c in conds)


def test_healthy_nodes_in_normal_stages_get_no_condition(scenario):
    nodes = {c.node for c in run_engine(scenario)}
    for healthy in ("N16", "N17", "N18", "N19", "N20", "N21"):  # job-b, stages 0 to 2
        assert healthy not in nodes  # absent is not the same as healthy


def test_silent_data_corruption_is_found_without_any_timing_problem(scenario):
    c = by_node(run_engine(scenario))[SDC_NODE]
    assert c.reason.value == "SDCSuspect"
    evidence = {e.signal: e.value for e in c.evidence}
    assert float(evidence["active_check_pass_rate"]) == 1.0  # it passes its idle checks
    assert float(evidence["peer_ratio"]) < 1.15  # and it is not slow


def test_corruption_is_not_called_without_cross_job_history(scenario):
    only_now = scenario.history.only_jobs(scenario.job_ids())
    assert SDC_NODE not in by_node(run_engine(scenario, history=only_now))  # no condition, not a false alarm


def test_one_old_blip_does_not_make_a_node_a_lemon(scenario):
    store = scenario.history
    assert store.get(DECOY_NODE).elevated_jobs() == 1
    assert DECOY_NODE not in by_node(run_engine(scenario))  # stage 0 to 2 of job-b, nothing fired


def test_no_verdict_names_a_healthy_node_as_node_fault(scenario):
    node_level = [c for c in run_engine(scenario) if c.attributed_to == "node"]
    assert {c.node for c in node_level} == {BAD_NODE, SDC_NODE}


def test_a_node_with_no_history_still_gets_a_timing_verdict(scenario):
    job = scenario.job("job-a")
    from node_verdict.history import HistoryStore

    conds = attribute(job.signals, job.node_of_rank, HistoryStore(), "t")
    assert by_node(conds)[BAD_NODE].reason.value == "NodeSuspect"


def test_engine_is_deterministic(scenario):
    first = [c.to_dict() for c in run_engine(scenario)]
    second = [c.to_dict() for c in run_engine(scenario)]
    assert first == second


def test_a_rank_that_is_slow_in_a_few_steps_gets_no_verdict(scenario):
    # job-c ranks are slow vs peers in 5 to 14 percent of steps. That is noise, not a node fault.
    conds = [c for c in run_engine(scenario) if c.job == "job-c"]
    assert {c.node for c in conds} == {"N27", "N28", "N29", "N30", "N31"}  # chip plus the slow stage


def test_sequence_skew_is_noted_on_the_stage_verdict_only_when_the_job_shows_it(scenario):
    msgs = {c.node: c.message for c in run_engine(scenario) if c.reason.value == "WorkloadImbalance"}
    assert "sequence lengths" in msgs["N28"]  # job-c: forward and backward move together
    assert "sequence lengths" not in msgs["N22"]  # job-b: stage partitioning only
