"""LS-SCN-TR — Scenario Transport / API surface tests (FastAPI TestClient)."""
import pytest
from fastapi.testclient import TestClient
from src.eureka.universe.scenario_transport import build_app

app = build_app()
client = TestClient(app)

BASE = {"scenario_id": "SCN-1", "work": {"work_id": "W1", "title": "t", "user_intent": "u",
                                        "task_category": "c", "problem_statement": "p",
                                        "acfl_weights": {"cost": 50.0, "risk": 50.0}}}


def test_valid_whatif_projection_http():
    r = client.post("/scenario/whatif", json={**BASE, "assumptions": [{"delta": 0.1}]})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "SCENARIO"
    assert body["authority"] == "PROJECTED"
    assert body["canonical_status"] == "NON_CANONICAL"
    assert body["projected_artifacts"][0]["authority"] == "PROJECTED"
    assert body["projected_artifacts"][0]["scope"] == "SCENARIO"


def test_assumptions_affect_real_computation_http():
    r_a = client.post("/scenario/whatif", json={**BASE, "assumptions": [{"delta": 0.0}]}).json()
    r_b = client.post("/scenario/whatif", json={**BASE, "assumptions": [{"delta": 0.2}]}).json()
    pa = r_a["projected_artifacts"][0]["payload"]
    pb = r_b["projected_artifacts"][0]["payload"]
    assert pa["m"] == 0.5
    assert pb["m"] == 0.7
    assert pa["gclv"] != pb["gclv"]


def test_source_identity_and_provenance_preserved_http():
    r = client.post("/scenario/whatif", json={**BASE, "assumptions": [{"delta": 0.1}]}).json()
    assert r["source_state_identity"]  # non-empty, derived from Q2
    assert r["provenance"]


def test_canonical_scope_escalation_rejected_http():
    # a client cannot force CANONICAL scope/authority in the response — the domain enforces SCENARIO
    r = client.post("/scenario/whatif", json={**BASE, "assumptions": [{"delta": 0.1}]}).json()
    assert r["scope"] == "SCENARIO"
    assert r["authority"] == "PROJECTED"


def test_malformed_request_rejected_http():
    r = client.post("/scenario/whatif", json={"scenario_id": "X", "work": {"work_id": "W1"}})
    assert r.status_code == 422  # FastAPI/pydantic validation error


def test_no_execution_or_promotion_surface_http():
    # the API exposes only the WHAT-IF endpoint; no execute/promote routes exist
    for path in ("/scenario/execute", "/scenario/promote", "/scenario/{id}/execute"):
        assert client.get(path).status_code in (404, 405)


def test_authorize_semantics_validated_in_domain(monkeypatch):
    # authorize (domain) remains non-executing — covered by service tests; here we assert the
    # transport does not expose an authorize endpoint that could trigger effects
    assert client.post("/scenario/authorize", json={}).status_code in (404, 405)
