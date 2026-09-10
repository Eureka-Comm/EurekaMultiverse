"""LS-SCN-PERS — bounded Scenario persistence (multi-request, file-backed JSON)."""
import json
import pytest
from fastapi.testclient import TestClient
from src.eureka.universe.scenario_transport import build_app
from src.eureka.universe.scenario_repository import ScenarioRepository


@pytest.fixture
def client(tmp_path):
    return TestClient(build_app(str(tmp_path)))


@pytest.fixture
def base():
    return {"scenario_id": "SCN-P", "work": {"work_id": "W1", "title": "t", "user_intent": "u",
                                             "task_category": "c", "problem_statement": "p",
                                             "acfl_weights": {"cost": 50.0, "risk": 50.0}}}


def test_multi_request_persist_retrieve_result(client, base):
    r1 = client.post("/scenario/whatif", json={**base, "assumptions": [{"delta": 0.1}]})
    assert r1.status_code == 200
    assert r1.json()["scope"] == "SCENARIO"
    assert r1.json()["projected_artifacts"][0]["payload"]["m"] == 0.6

    r2 = client.get("/scenario/SCN-P")
    assert r2.status_code == 200
    assert r2.json()["source_state_identity"] == r1.json()["source_state_identity"]

    r3 = client.post("/scenario/SCN-P/project", json={"work": base["work"]})
    assert r3.status_code == 200
    assert r3.json()["authority"] == "PROJECTED"

    r4 = client.get("/scenario/SCN-P/result")
    assert r4.status_code == 200
    assert r4.json()["canonical_status"] == "NON_CANONICAL"
    assert r4.json()["projected_artifacts"][0]["authority"] == "PROJECTED"


def test_persistence_is_durable_cross_instance(client, tmp_path, base):
    client.post("/scenario/whatif", json={**base, "assumptions": [{"delta": 0.1}]})
    # A brand-new repository/service pointing at the same storage dir reads it from disk.
    repo = ScenarioRepository(str(tmp_path))
    sc = repo.get_scenario("SCN-P")
    res = repo.get_result("SCN-P")
    assert sc is not None and sc.source_state_identity
    assert res is not None and res.is_non_canonical is True


def test_assumptions_affect_real_computation_multi_request(client, base):
    a = client.post("/scenario/whatif", json={**base, "scenario_id": "SNA", "assumptions": [{"delta": 0.0}]}).json()
    b = client.post("/scenario/whatif", json={**base, "scenario_id": "SNB", "assumptions": [{"delta": 0.2}]}).json()
    pa = client.get("/scenario/SNA/result").json()["projected_artifacts"][0]["payload"]
    pb = client.get("/scenario/SNB/result").json()["projected_artifacts"][0]["payload"]
    assert pa["m"] == 0.5
    assert pb["m"] == 0.7
    assert pa["gclv"] != pb["gclv"]


def test_reproject_same_source_stays_non_canonical(client, base):
    client.post("/scenario/whatif", json={**base, "assumptions": [{"delta": 0.1}]})
    r = client.post("/scenario/SCN-P/project", json={"work": base["work"]})
    assert r.status_code == 200
    assert r.json()["authority"] == "PROJECTED"
    assert r.json()["projected_artifacts"][0]["scope"] == "SCENARIO"


def test_stale_source_fails_closed_at_service_level(client, base):
    # Service-level staleness is authoritative: a source whose fingerprint-relevant content
    # (result) differs from the scenario's source fails closed. (Transport WorkInput carries only
    # work + acfl, which are NOT in the Q2 fingerprint, so API-level staleness needs a fuller
    # WorkInput; proven deterministically at the service/domain layer.)
    from src.eureka.universe.work_model import EurekaWork
    from src.eureka.universe.canonical_state import CanonicalWorkState, WorkResult
    from src.eureka.universe.scenario_foundation import Scenario
    from src.eureka.universe.scenario_lifecycle import ScenarioLifecycle, LifecycleTransitionError
    src_a = CanonicalWorkState(work=EurekaWork(work_id="W1", title="t", user_intent="u",
                                              task_category="c", problem_statement="p"))
    sc = Scenario.from_source("SCN-X", src_a, assumptions=[{"delta": 0.1}])
    src_b = CanonicalWorkState(work=EurekaWork(work_id="W1", title="t", user_intent="u",
                                               task_category="c", problem_statement="p"))
    src_b.result = WorkResult(result_id="R2", work_id="W1", status="AVAILABLE", summary="x")
    lc = ScenarioLifecycle.create(sc).ready(src_a).run()
    with pytest.raises((LifecycleTransitionError, RuntimeError)):
        lc.validate(src_b)


def test_persisted_result_preserves_q3_authority(client, tmp_path, base):
    client.post("/scenario/whatif", json={**base, "assumptions": [{"delta": 0.1}]})
    # tamper attempt: hand-write a result with canonical authority and confirm it is rejected on read
    result_path = str(tmp_path / "SCN-P.result.json")
    with open(result_path) as f:
        data = json.load(f)
    data["projected_artifacts"][0]["authority"] = "CANONICAL"
    with open(result_path, "w") as f:
        json.dump(data, f)
    with pytest.raises(Exception):  # pydantic validation rejects canonical authority (fail closed)
        ScenarioRepository(str(tmp_path)).get_result("SCN-P")


def test_missing_scenario_returns_404(client):
    assert client.get("/scenario/NOPE").status_code == 404
    assert client.get("/scenario/NOPE/result").status_code == 404
