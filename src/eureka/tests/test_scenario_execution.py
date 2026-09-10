"""LS-SCN-EXEC — Governed HUMAN decision -> REAL_EXECUTION under Q4 -> observable effect.

The REAL effect is a governed artifact materialization (a durable, provenance-bearing file is
written to a governed output dir). The proof for a real effect is BEFORE != AFTER on the filesystem,
not just an HTTP 200. Every non-success path is fail-closed (no effect, no false success).
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
from src.eureka.universe.scenario_execution import execute_gov, resolve_authorized_action, ACTION_MATERIALIZE
from src.eureka.universe.scenario_decision import DecisionType
from src.eureka.universe.effect_policy import default_boundary, DryRunContext, ExecutionMode, PolicyError, guarded_dump_json
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, StructuredFinding, WorkResult

# ONE isolated, durable Work authority for this module (no pollution of the production store).
_WORK_STORE = WorkStore(tempfile.mkdtemp())


def _seed_real_work(work_id="W-EXEC"):
    real = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="Real Work", user_intent="analyze dataset",
        task_category="DESCRIPTOR", problem_statement="Analyze dataset X"))
    real.knowledge.findings.append(StructuredFinding(finding_id="F-1", statement="correlation found",
                                                     finding_type="RELATIONAL", evidence_refs=["EVI-1"]))
    real.result = WorkResult(result_id="R-1", work_id=work_id, summary="done",
                             status="AVAILABLE", confidence=0.9)
    _WORK_STORE[work_id] = real
    return real


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as td:
        artifact_dir = os.path.join(td, "artifacts")
        service = ScenarioService(repository=ScenarioRepository(td), artifact_dir=artifact_dir)
        app = FastAPI()
        app.include_router(make_router(service, work_resolver=lambda work_id: _WORK_STORE.get(work_id)), prefix="/api")
        yield TestClient(app), artifact_dir


def _whatif_and_authorize(client, scenario_id="SCN-EXEC"):
    client.post("/api/scenario/whatif", json={"scenario_id": scenario_id, "work_id": "W-EXEC",
                                              "assumptions": [{"delta": 0.1}]})
    client.post(f"/api/scenario/{scenario_id}/authorize", json={"work_id": "W-EXEC",
                                                                "decision_type": "CONFIRM",
                                                                "rationale": "ok", "human_actor": "a"})


def test_execute_produces_real_observable_effect(client):
    tc, artifact_dir = client
    _seed_real_work()
    _whatif_and_authorize(tc, "SCN-EXEC")
    # BEFORE: no artifact
    action_id = f"{ACTION_MATERIALIZE}:SCN-EXEC"
    path = os.path.join(artifact_dir, f"SCN-EXEC-{action_id}.json")
    assert not os.path.exists(path)
    r = tc.post("/api/scenario/SCN-EXEC/execute", json={"work_id": "W-EXEC"})
    assert r.status_code == 200
    e = r.json()
    assert e["status"] == "SUCCEEDED"
    assert e["authority"] == "HUMAN_DECISION"
    assert e["scope"] == "SCENARIO"
    assert e["canonical_status"] == "NON_CANONICAL"
    assert e["governance"]["mode"] == "REAL_EXECUTION"
    assert e["governance"]["decision"] == "ALLOW"
    assert e["governance"]["effect_class"] == "MUTATE"
    assert e["effect"]["exists"] is True
    # AFTER: the artifact exists with real content (BEFORE != AFTER)
    assert os.path.exists(path)
    import json
    content = json.load(open(path, "r", encoding="utf-8"))
    assert content["scenario_id"] == "SCN-EXEC"
    assert content["authority"] == "HUMAN_DECISION"
    assert content["canonical_status"] == "NON_CANONICAL"
    assert content["source_state_identity"] == e["source_state_identity"]
    # retrievable execution + audit trail
    got = tc.get("/api/scenario/SCN-EXEC/execution").json()
    assert got["execution_id"] == e["execution_id"]
    assert tc.get("/api/scenario/executions").status_code == 200


def test_execute_stale_source_fails_closed_no_effect(client):
    tc, artifact_dir = client
    real = _seed_real_work()
    _whatif_and_authorize(tc, "SCN-STALE")
    real.knowledge.findings.append(StructuredFinding(finding_id="F-2", statement="new info",
                                                     finding_type="RELATIONAL"))
    r = tc.post("/api/scenario/SCN-STALE/execute", json={"work_id": "W-EXEC"})
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["error"] == "STALE_SOURCE"
    assert body["detail"]["execution"]["status"] == "REJECTED"
    assert body["detail"]["execution"]["effect"] == {}
    # no artifact written
    assert not (os.path.isdir(artifact_dir) and [f for f in os.listdir(artifact_dir) if f.startswith("SCN-STALE")])


def test_execute_discarded_scenario_rejected_no_effect(client):
    tc, artifact_dir = client
    _seed_real_work()
    tc.post("/api/scenario/whatif", json={"scenario_id": "SCN-DISC", "work_id": "W-EXEC",
                                          "assumptions": [{"delta": 0.1}]})
    tc.post("/api/scenario/SCN-DISC/discard", json={"work_id": "W-EXEC", "decision_type": "REJECT"})
    r = tc.post("/api/scenario/SCN-DISC/execute", json={"work_id": "W-EXEC"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "ACTION_NOT_AUTHORIZED"
    assert not (os.path.isdir(artifact_dir) and [f for f in os.listdir(artifact_dir) if f.startswith("SCN-DISC")])


def test_execute_without_decision_fails_closed(client):
    tc, _ = client
    _seed_real_work()
    tc.post("/api/scenario/whatif", json={"scenario_id": "SCN-NODEC", "work_id": "W-EXEC",
                                          "assumptions": [{"delta": 0.1}]})
    r = tc.post("/api/scenario/SCN-NODEC/execute", json={"work_id": "W-EXEC"})
    assert r.status_code == 404
    assert r.json()["detail"]["error"].startswith("DECISION_NOT_FOUND")


def test_execute_unknown_scenario_fails_closed(client):
    tc, _ = client
    _seed_real_work()
    r = tc.post("/api/scenario/SCN-NOPE/execute", json={"work_id": "W-EXEC"})
    assert r.status_code == 404


def test_execute_requires_source_fails_closed(client):
    tc, _ = client
    _seed_real_work()
    _whatif_and_authorize(tc, "SCN-NSRC")
    r = tc.post("/api/scenario/SCN-NSRC/execute", json={})
    assert r.status_code == 422


def test_execute_duplicate_is_idempotent(client):
    tc, artifact_dir = client
    _seed_real_work()
    _whatif_and_authorize(tc, "SCN-DUP")
    first = tc.post("/api/scenario/SCN-DUP/execute", json={"work_id": "W-EXEC"})
    assert first.status_code == 200
    second = tc.post("/api/scenario/SCN-DUP/execute", json={"work_id": "W-EXEC"})
    assert second.status_code == 200
    assert first.json()["execution_id"] == second.json()["execution_id"]
    # exactly ONE artifact file for this scenario (no duplicate effect)
    files = [f for f in os.listdir(artifact_dir) if f.startswith("SCN-DUP")]
    assert len(files) == 1


def test_execute_preserves_canonical_isolation(client):
    tc, _ = client
    _seed_real_work()
    _whatif_and_authorize(tc, "SCN-ISO")
    tc.post("/api/scenario/SCN-ISO/execute", json={"work_id": "W-EXEC"})
    sc = tc.get("/api/scenario/SCN-ISO").json()
    assert sc["status"] == "HYPOTHETICAL"
    assert sc["scope"] == "SCENARIO"
    res = tc.get("/api/scenario/SCN-ISO/result").json()
    assert res["authority"] == "PROJECTED"
    assert res["canonical_status"] == "NON_CANONICAL"
    for a in res["projected_artifacts"]:
        assert a["authority"] == "PROJECTED"


def test_execute_ignores_client_authority_injection(client):
    tc, _ = client
    _seed_real_work()
    _whatif_and_authorize(tc, "SCN-FORGED")
    r = tc.post("/api/scenario/SCN-FORGED/execute", json={
        "work_id": "W-EXEC", "authority": "CANONICAL", "scope": "CANONICAL",
        "canonical_status": "CANONICAL", "execute": True, "promote": True,
        "bypass_governance": True, "execution_mode": "REAL"})
    assert r.status_code == 200
    e = r.json()
    assert e["authority"] == "HUMAN_DECISION"
    assert e["scope"] == "SCENARIO"
    assert e["canonical_status"] == "NON_CANONICAL"
    assert e["status"] == "SUCCEEDED"  # governed by the recorded decision, not the injection


def test_scenario_execution_blocks_dry_run_via_q4():
    # Q4 authority: a MUTATE scenario.execution under DRY_RUN must BLOCK (and write nothing).
    boundary = default_boundary()
    ctx = DryRunContext(capability_id="scenario.execution", target="scenario-artifact:X",
                        mode=ExecutionMode.DRY_RUN, authorization="HUMAN_DECISION:D1")
    with pytest.raises(PolicyError) as exc:
        boundary.enforce(ctx)
    assert exc.value.reason_code == "MUTATE_IN_DRY_RUN"


def test_execute_gov_requires_authorized_confirm_decision(client):
    tc, _ = client
    _seed_real_work()
    # A REJECT decision (lifecycle DISCARDED) resolves to NO authorizable action.
    tc.post("/api/scenario/whatif", json={"scenario_id": "SCN-REJ", "work_id": "W-EXEC",
                                          "assumptions": [{"delta": 0.1}]})
    tc.post("/api/scenario/SCN-REJ/discard", json={"work_id": "W-EXEC", "decision_type": "REJECT"})
    r = tc.post("/api/scenario/SCN-REJ/execute", json={"work_id": "W-EXEC"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "ACTION_NOT_AUTHORIZED"
