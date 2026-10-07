from node_verdict.conditions import API_VERSION, REASON_CODES_V1, Evidence, NodeCondition, ReasonCode


def test_reason_codes_are_a_frozen_contract():
    # Renaming a reason code breaks customer automation. If this fails on purpose,
    # it needs a new API version, not a quiet edit.
    assert {r.value for r in ReasonCode} == REASON_CODES_V1
    assert REASON_CODES_V1 == {"NodeLemon", "NodeSuspect", "SDCSuspect", "WorkloadImbalance"}


def test_condition_serializes_to_kubernetes_shape():
    c = NodeCondition(
        node="N00", job="job-a", reason=ReasonCode.NODE_LEMON, message="m", confidence="high",
        last_transition_time="2026-10-06T00:00:00Z", evidence=(Evidence("peer_ratio", "2.35", "n"),),
    )
    d = c.to_dict()
    assert d["apiVersion"] == API_VERSION
    cond = d["condition"]
    assert cond["type"] == "NodeVerdict"
    assert cond["status"] == "True"
    assert cond["reason"] == "NodeLemon"
    assert cond["attributedTo"] == "node"
    assert cond["lastTransitionTime"] == "2026-10-06T00:00:00Z"
    assert cond["evidence"][0] == {"signal": "peer_ratio", "value": "2.35", "note": "n"}


def test_workload_verdict_is_attributed_to_the_job():
    c = NodeCondition("N22", "job-b", ReasonCode.WORKLOAD_IMBALANCE, "m", "high", "t")
    assert c.attributed_to == "job"
