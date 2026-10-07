import json

from node_verdict.export import DEFAULT_OUT, build_export, dumps


def test_web_data_matches_a_fresh_export():
    # The web demo renders this file and decides nothing. If this fails, run
    # `python scripts/export_json.py` and commit the result.
    assert DEFAULT_OUT.exists(), "run python scripts/export_json.py"
    committed = DEFAULT_OUT.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == dumps(build_export())


def test_export_has_what_the_demo_needs():
    data = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    assert len(data["pool"]) == 32
    assert [j["id"] for j in data["jobs"]] == ["job-a", "job-b", "job-c"]
    assert [p["name"] for p in data["policies"]] == ["naive", "naive+checkpoint", "peer-aware", "attributed"]
    reasons = {v["node"]: v["condition"]["reason"] for v in data["verdicts"]["withHistory"]}
    assert reasons["N00"] == "NodeLemon" and reasons["N27"] == "SDCSuspect"
    assert "N27" not in {v["node"] for v in data["verdicts"]["noHistory"]}
    assert data["robustness"]["healthyNodesEverChanged"] == 0
    assert {r["code"] for r in data["reasonCodes"]} == {"NodeLemon", "NodeSuspect", "SDCSuspect", "WorkloadImbalance"}
