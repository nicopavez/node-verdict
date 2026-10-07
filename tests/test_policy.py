from node_verdict.conditions import NodeCondition, ReasonCode
from node_verdict.policy import INFORM, QUARANTINE, REPLACE, WATCH, PolicyConfig, plan


def cond(node, reason, job="job-x"):
    return NodeCondition(node, job, reason, "m", "high", "t")


def test_default_actions_match_the_proposal():
    actions = plan(
        [
            cond("N1", ReasonCode.NODE_LEMON, "j1"),
            cond("N2", ReasonCode.SDC_SUSPECT, "j2"),
            cond("N3", ReasonCode.NODE_SUSPECT, "j3"),
            cond("N4", ReasonCode.WORKLOAD_IMBALANCE, "j4"),
        ],
        pool_size=32, spares=4, nodes_per_job={"j1": 16, "j2": 16, "j3": 16, "j4": 16},
    )
    assert [a.kind for a in actions] == [REPLACE, QUARANTINE, WATCH, INFORM]
    assert all(a.status == "planned" for a in actions)


def test_workload_verdict_never_changes_a_node():
    actions = plan([cond("N4", ReasonCode.WORKLOAD_IMBALANCE)], 32, 4, {"job-x": 8})
    assert not any(a.changes_node for a in actions)


def test_no_spare_blocks_the_replacement():
    actions = plan([cond("N1", ReasonCode.NODE_LEMON, "j1")], 32, 0, {"j1": 16})
    assert actions[0].status == "blocked_no_spare"
    assert not actions[0].changes_node


def test_correlation_guard_halts_automation_when_many_nodes_flag_at_once():
    conds = [cond(f"N{i}", ReasonCode.NODE_LEMON) for i in range(4)]
    actions = plan(conds, pool_size=32, spares=8, nodes_per_job={"job-x": 8})  # 4 of 8 nodes
    assert all(a.status == "held_correlated" and a.kind == WATCH for a in actions)


def test_fleet_cap_limits_concurrent_changes():
    conds = [cond(f"N{i}", ReasonCode.NODE_LEMON, f"j{i}") for i in range(5)]
    sizes = {f"j{i}": 100 for i in range(5)}
    actions = plan(conds, pool_size=10, spares=10, nodes_per_job=sizes, cfg=PolicyConfig(max_concurrent_fraction=0.2))
    assert [a.status for a in actions] == ["planned", "planned", "capped", "capped", "capped"]


def test_actions_are_editable_config():
    cfg = PolicyConfig(actions={**PolicyConfig().actions, ReasonCode.NODE_LEMON: QUARANTINE})
    actions = plan([cond("N1", ReasonCode.NODE_LEMON, "j1")], 32, 4, {"j1": 16}, cfg)
    assert actions[0].kind == QUARANTINE
