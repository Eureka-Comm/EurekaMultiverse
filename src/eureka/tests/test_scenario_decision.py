"""LS-SCN-DEC — Governed HUMAN decision workflow + audit trail over Scenario WHAT-IF.

Exercises the REAL decision path (transport -> service -> lifecycle -> repository -> decision model):
- a human can record an explicit (record-only) AUTHORIZE / DISCARD decision on a scenario,
- authority/scope/canonical_status are SERVER-derived (the client never supplies them),
- the decision is durable and retrievable (audit trail),
- it never promotes / executes / canonicalizes (the scenario stays non-canonical),
- fail-closed on unknown scenario, missing source, and re-opening a terminal scenario.
"""
import os
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.eureka.universe.work_store import WorkStore
from src.eureka.universe.scenario_transport import make_router
from src.eureka.universe.scenario_service import ScenarioService
from src.eureka.universe.scenario_repository import ScenarioRepository
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, StructuredFinding, WorkResult

# ONE isolated, durable Work authority for this module (no pollution of the production store).
_WORK_STORE = WorkStore(tempfile.mkdtemp())


def _build_app(tmp_dir):
    service = ScenarioService(repository=ScenarioRepository(tmp_dir))
    app = FastAPI()
    app.include_router(make_router(service, work_resolver=lambda work_id: _WORK_STORE.get(work_id)), prefix="/api")
    return app, service


def _seed_real_work(work_id="W-DEC"):
    real = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="Real Work", user_intent="analyze dataset",
        task_category="DESCRIPTOR", problem_statement="Analyze dataset X"))
    real.knowledge.findings.append(StructuredFinding(
        finding_id="F-1", statement="correlation found", finding_type="RELATIONAL",
        evidence_refs=["EVI-1"]))
    real.result = WorkResult(result_id="R-1", work_id=work_id, summary="done",
                             status="AVAILABLE", confidence=0.9)
    _WORK_STORE[work_id] = real
    return real


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as td:
        app, service = _build_app(td)
        yield TestClient(app)


def test_authorize_real_work_seam_records_human_decision(client):
    _seed_real_work()
    # create a scenario from the REAL work
    tr = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-DEC",
                                                   "work_id": "W-DEC", "assumptions": [{"delta": 0.1}]})
    assert tr.status_code == 200
    scenario = tr.json()
    # human RECORDS an explicit decision (record-only)
    r = client.post("/api/scenario/SCN-DEC/authorize", json={
        "work_id": "W-DEC", "decision_type": "CONFIRM",
        "rationale": "The human accepts this projected outcome as a working hypothesis.",
        "human_actor": "analyst-1", "selected_artifact_id": "PRJ-ACFL"})
    assert r.status_code == 200
    d = r.json()
    # server-derived authority (client cannot claim it)
    assert d["authority"] == "HUMAN_DECISION"
    assert d["scope"] == "SCENARIO"
    assert d["canonical_status"] == "NON_CANONICAL"
    assert d["lifecycle_state"] == "AUTHORIZED"
    assert d["scenario_id"] == "SCN-DEC"
    assert d["source_state_identity"] == scenario["source_state_identity"]
    assert "authority:HUMAN_DECISION" in d["provenance"]
    # durable audit trail
    got = client.get("/api/scenario/SCN-DEC/decision").json()
    assert got["decision_id"] == d["decision_id"]
    assert client.get("/api/scenario/decisions").status_code == 200


def test_authorize_does_not_promote_or_mutate_scenario(client):
    _seed_real_work()
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-NOPROM", "work_id": "W-DEC",
                                              "assumptions": [{"delta": 0.1}]})
    client.post("/api/scenario/SCN-NOPROM/authorize", json={"work_id": "W-DEC", "decision_type": "CONFIRM"})
    # the scenario itself stays non-canonical (hypothetical, PROJECTED artifacts, no promotion)
    sc = client.get("/api/scenario/SCN-NOPROM").json()
    assert sc["status"] == "HYPOTHETICAL"
    assert sc["scope"] == "SCENARIO"
    res = client.get("/api/scenario/SCN-NOPROM/result").json()
    assert res["authority"] == "PROJECTED"
    assert res["canonical_status"] == "NON_CANONICAL"
    for a in res["projected_artifacts"]:
        assert a["authority"] == "PROJECTED"
    # the recorded decision contains no promotion/execution semantics
    dec = client.get("/api/scenario/SCN-NOPROM/decision").json()
    for banned in ("promote", "execute", "canonicalize", "REAL_EXECUTION"):
        assert banned not in dec


def test_discard_records_envoy_and_audit(client):
    _seed_real_work()
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-DISC", "work_id": "W-DEC",
                                              "assumptions": [{"delta": 0.1}]})
    r = client.post("/api/scenario/SCN-DISC/discard", json={"work_id": "W-DEC", "decision_type": "REJECT",
                                                            "rationale": "Not enough evidence.", "human_actor": "analyst-2"})
    assert r.status_code == 200
    d = r.json()
    assert d["lifecycle_state"] == "DISCARDED"
    assert d["authority"] == "HUMAN_DECISION"
    assert d["canonical_status"] == "NON_CANONICAL"
    assert d["decision_type"] == "REJECT"
    assert client.get("/api/scenario/SCN-DISC/decision").json()["scenario_id"] == "SCN-DISC"


def test_authorize_unknown_scenario_fails_closed(client):
    _seed_real_work()
    r = client.post("/api/scenario/SCN-NOPE/authorize", json={"work_id": "W-DEC", "decision_type": "CONFIRM"})
    assert r.status_code == 404
    assert "SCENARIO_NOT_FOUND" in r.json()["detail"]["error"]


def test_authorize_requires_source_fails_closed(client):
    _seed_real_work()
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-NOSRC", "work_id": "W-DEC",
                                              "assumptions": [{"delta": 0.1}]})
    # neither work_id nor work -> no source -> fail closed
    r = client.post("/api/scenario/SCN-NOSRC/authorize", json={"decision_type": "CONFIRM"})
    assert r.status_code == 422


def test_authorize_terminal_state_fails_closed(client):
    _seed_real_work()
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-ONCE", "work_id": "W-DEC",
                                              "assumptions": [{"delta": 0.1}]})
    assert client.post("/api/scenario/SCN-ONCE/authorize", json={"work_id": "W-DEC", "decision_type": "CONFIRM"}).status_code == 200
    # a second decision on a terminal (AUTHORIZED) scenario must be rejected (no re-open)
    r = client.post("/api/scenario/SCN-ONCE/discard", json={"work_id": "W-DEC", "decision_type": "REJECT"})
    assert r.status_code == 409


def test_decision_unknown_not_found(client):
    r = client.get("/api/scenario/SCN-UNDECIDED/decision")
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "DECISION_NOT_FOUND"


def test_authorize_stale_source_fails_closed(client):
    real = _seed_real_work()
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-STALE", "work_id": "W-DEC",
                                              "assumptions": [{"delta": 0.1}]})
    # the canonical work CHANGES after the scenario was created -> source is now STALE
    real.knowledge.findings.append(StructuredFinding(finding_id="F-2", statement="new info",
                                                     finding_type="RELATIONAL"))
    r = client.post("/api/scenario/SCN-STALE/authorize", json={"work_id": "W-DEC", "decision_type": "CONFIRM"})
    assert r.status_code == 409
    assert "STALE_SOURCE" in r.json()["detail"]["error"]


def test_authorize_ignores_client_authority_claims(client):
    _seed_real_work()
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-FORGED", "work_id": "W-DEC",
                                              "assumptions": [{"delta": 0.1}]})
    # the client attempts to claim CANONICAL authority/scope/status -> server derives its own
    r = client.post("/api/scenario/SCN-FORGED/authorize", json={
        "work_id": "W-DEC", "decision_type": "CONFIRM",
        "rationale": "x", "human_actor": "a",
        "authority": "CANONICAL", "scope": "CANONICAL", "canonical_status": "CANONICAL"})
    assert r.status_code == 200
    d = r.json()
    assert d["authority"] == "HUMAN_DECISION"
    assert d["scope"] == "SCENARIO"
    assert d["canonical_status"] == "NON_CANONICAL"
