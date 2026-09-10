"""LS-SCN-CMP — Multi-scenario result comparison (evidence aggregation, non-canonical)."""
import pytest
from fastapi.testclient import TestClient
from src.eureka.universe.scenario_transport import build_app
from src.eureka.universe.scenario_repository import ScenarioRepository
from src.eureka.universe.scenario_comparison import compare_results
from src.eureka.universe.projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass, CanonicalStatus


@pytest.fixture
def client(tmp_path):
    return TestClient(build_app(str(tmp_path)))


def _mk_scenario(i, srcid):
    from src.eureka.universe.scenario_foundation import Scenario
    return Scenario(scenario_id=i, source_state_identity=srcid, provenance=["p"])


def _mk_result(i, srcid, value, m):
    from src.eureka.universe.scenario_runtime import ScenarioRuntimeResult
    pa = ProjectedArtifact(artifact_id=f"P-{i}", artifact_kind="PREDICTION",
                           source_state_identity=srcid, provenance=["p"],
                           payload={"gclv": value, "m": m})
    return ScenarioRuntimeResult(scenario_id=i, source_state_identity=srcid, projected_artifacts=[pa])


def test_multi_scenario_compare_e2e(client):
    base = {"work": {"work_id": "W1", "title": "t", "user_intent": "u", "task_category": "c",
                     "problem_statement": "p", "acfl_weights": {"cost": 50.0, "risk": 50.0}}}
    for sid, delta in (("SNA", 0.0), ("SNB", 0.1), ("SNC", 0.2)):
        client.post("/scenario/whatif", json={**base, "scenario_id": sid, "assumptions": [{"delta": delta}]})
    r = client.post("/scenario/compare", json={"scenario_ids": ["SNA", "SNB", "SNC"],
                                               "baseline_scenario_id": "SNA"})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "SCENARIO"
    assert body["authority"] == "PROJECTED"
    assert body["canonical_status"] == "NON_CANONICAL"
    # input order preserved
    assert body["scenario_ids"] == ["SNA", "SNB", "SNC"]
    # metrics differ per assumption
    by_id = {e["scenario_id"]: e["metrics"] for e in body["scenarios"]}
    assert by_id["SNA"]["m"] == 0.5
    assert by_id["SNB"]["m"] == 0.6
    assert by_id["SNC"]["m"] == 0.7
    assert by_id["SNA"]["gclv"] != by_id["SNB"]["gclv"] != by_id["SNC"]["gclv"]


def test_compare_is_deterministic(client):
    base = {"work": {"work_id": "W1", "title": "t", "user_intent": "u", "task_category": "c",
                     "problem_statement": "p", "acfl_weights": {"cost": 50.0, "risk": 50.0}}}
    for sid, delta in (("SNA", 0.0), ("SNB", 0.1)):
        client.post("/scenario/whatif", json={**base, "scenario_id": sid, "assumptions": [{"delta": delta}]})
    a = client.post("/scenario/compare", json={"scenario_ids": ["SNA", "SNB"]}).json()
    b = client.post("/scenario/compare", json={"scenario_ids": ["SNA", "SNB"]}).json()
    assert a["metric_comparisons"] == b["metric_comparisons"]


def test_compare_empty_and_duplicate(client):
    assert client.post("/scenario/compare", json={"scenario_ids": []}).status_code == 422
    assert client.post("/scenario/compare", json={"scenario_ids": ["A", "A"]}).status_code == 422


def test_compare_missing_scenario_404(client):
    assert client.post("/scenario/compare", json={"scenario_ids": ["NOPE"]}).status_code == 404


def test_compare_no_recommendation_or_winner(client):
    base = {"work": {"work_id": "W1", "title": "t", "user_intent": "u", "task_category": "c",
                     "problem_statement": "p", "acfl_weights": {"cost": 50.0, "risk": 50.0}}}
    client.post("/scenario/whatif", json={**base, "scenario_id": "SNA", "assumptions": [{"delta": 0.0}]})
    body = client.post("/scenario/compare", json={"scenario_ids": ["SNA"]}).json()
    for banned in ("best_scenario", "recommended_scenario", "selected_scenario", "winning_scenario", "recommendation", "decision", "promote"):
        assert banned not in body


def test_compare_incomparable_source_state(tmp_path):
    repo = ScenarioRepository(str(tmp_path))
    repo.save_scenario(_mk_scenario("A", "hashA"))
    repo.save_result(_mk_result("A", "hashA", 1.0, 0.5))
    repo.save_scenario(_mk_scenario("B", "hashB"))
    repo.save_result(_mk_result("B", "hashB", 2.0, 0.6))
    with pytest.raises(ValueError):
        compare_results(repo, ["A", "B"])


def test_compare_result_mismatch(tmp_path):
    repo = ScenarioRepository(str(tmp_path))
    repo.save_scenario(_mk_scenario("A", "hashA"))
    repo.save_result(_mk_result("A", "hashA", 1.0, 0.5))
    repo.save_scenario(_mk_scenario("B", "hashA"))  # B shares A's source
    repo.save_result(_mk_result("B", "WRONG", 2.0, 0.6))  # B's result source mismatches B's scenario
    with pytest.raises(ValueError):
        compare_results(repo, ["A", "B"])
