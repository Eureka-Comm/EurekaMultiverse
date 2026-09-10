"""LS-SCN-OBS — Real observability / durable audit trail projection (READ-ONLY).

The audit endpoint composes the EXISTING authorities (WorkStore + ScenarioRepository) into a single
read-only projection: Work (linked via Q2) -> Scenario -> WHAT-IF (multi-metric artifacts) -> Decision ->
Execution. It must be read-only (no canonical mutation, no writes), honest about NOT_RECORDED stages
(comparison is not stored), and restart-safe (the projection is rebuilt from durable storage).
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
from src.eureka.universe.canonical_state import (CanonicalWorkState, StructuredFinding, WorkResult,
                                                 PredictionKnowledge, PredictivePredicate, PredictiveUncertainty)
from src.eureka.universe.prescription_model import (ValidatedPrescription, PrescriptionAlternative, DecisionRule)
from src.eureka.universe.math_ir import GCLVMembership, Variable
from src.eureka.universe.canonical_identity import canonical_state_fingerprint


def _mk_real(work_id="W-OBS"):
    real = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="R", user_intent="u",
                                              task_category="DESCRIPTOR", problem_statement="p"))
    real.knowledge.findings.append(StructuredFinding(finding_id="F-1", statement="corr",
                                                     finding_type="RELATIONAL", evidence_refs=["EVI-1"]))
    real.result = WorkResult(result_id="R-1", work_id=work_id, summary="d", status="AVAILABLE", confidence=0.9)
    real.acfl.weights = {"cost": 50.0, "risk": 50.0}
    real.predictive_knowledge.predicates.append(PredictivePredicate(
        predicate_id="PP-1", target="revenue",
        logical_structure=GCLVMembership(input=Variable(name="revenue"), alpha=1.0, gamma=0.5, m=0.5),
        mse=0.01, status="VALIDATED", provenance=["ACFL_ENGINE_V5.1"]))
    real.predictive_knowledge.predictions.append(PredictionKnowledge(
        prediction_id="PRED-1", target_variable="revenue", predicted_value=0.7, model_type="ACFL_ENGINE",
        model_definition="MSE=0.01", validation_status="VALIDATED", predictor_variables=["revenue"],
        uncertainty=PredictiveUncertainty(status="NOT_AVAILABLE"), provenance=["Task[t]"]))
    real.predictive_knowledge.status = "FROZEN"
    a1 = PrescriptionAlternative(alternative_id="ALT-1", description="inc", score=0.8)
    a2 = PrescriptionAlternative(alternative_id="ALT-2", description="hold", score=0.5)
    real.prescriptive_knowledge.prescriptions.append(ValidatedPrescription(
        prescription_id="PRES-1", objective="max", alternatives=[a1, a2], applicable_criteria=[],
        constraints=[], decision_rule=DecisionRule(status="DOCUMENTED"), supporting_predictions=["PRED-1"],
        supporting_knowledge=[], rationale="r", authority="HUMAN", provenance=["EMPrescriptor"],
        validation_status="EVALUATED", selected_alternative=a1))
    real.prescriptive_knowledge.status = "FROZEN"
    return real


@pytest.fixture
def app_and_store():
    with tempfile.TemporaryDirectory() as td:
        work_dir = tempfile.mkdtemp()
        store = WorkStore(work_dir)
        service = ScenarioService(repository=ScenarioRepository(td), artifact_dir=os.path.join(td, "art"))
        app = FastAPI()
        app.include_router(make_router(service, work_resolver=lambda wid: store.get(wid)), prefix="/api")
        yield TestClient(app), store


def _run_pipeline(client, store, sid="SCN-OBS", work_id="W-OBS"):
    real = _mk_real(work_id)
    store[work_id] = real
    client.post("/api/scenario/whatif", json={"scenario_id": sid, "work_id": work_id,
                                              "assumptions": [{"delta": 0.1}]})
    client.post(f"/api/scenario/{sid}/authorize", json={"work_id": work_id, "decision_type": "CONFIRM",
                                                        "rationale": "ok", "human_actor": "a"})
    client.post(f"/api/scenario/{sid}/execute", json={"work_id": work_id})


def test_audit_shows_full_pipeline(app_and_store):
    client, store = app_and_store
    _run_pipeline(client, store)
    r = client.get("/api/scenario/SCN-OBS/audit?work_id=W-OBS")
    assert r.status_code == 200
    a = r.json()
    assert a["scenario_id"] == "SCN-OBS"
    # WORK linked via Q2 (Recorded)
    assert a["work"] is not None and a["work"]["linked_to_scenario"] is True
    stages = {s["stage"]: s["status"] for s in a["stages"]}
    assert stages["WORK"] == "RECORDED"
    assert stages["SCENARIO"] == "RECORDED"
    assert stages["WHAT_IF"] == "RECORDED"
    assert stages["DECISION"] == "RECORDED"
    assert stages["EXECUTION"] == "RECORDED"
    assert stages["COMPARE"] == "NOT_RECORDED"     # comparison is computed on demand, not stored
    # real projected artifacts
    ids = [x["artifact_id"] for x in a["projected_artifacts"]]
    assert "PRJ-ACFL" in ids
    assert "PRJ-PREDICTIVE" in ids
    assert "PRJ-PRESCRIPTIVE" in ids
    # decision + execution present
    assert a["decision"]["authority"] == "HUMAN_DECISION"
    assert a["decision"]["lifecycle_state"] == "AUTHORIZED"
    assert a["execution"]["status"] == "SUCCEEDED"
    assert a["execution"]["governance"]["mode"] == "REAL_EXECUTION"


def test_audit_is_read_only_no_mutation(app_and_store):
    client, store = app_and_store
    _run_pipeline(client, store)
    real = store["W-OBS"]
    fp_before = canonical_state_fingerprint(real)
    rev_before = real.revision
    # multiple audit reads must not mutate the canonical / scenario / decision / execution
    client.get("/api/scenario/SCN-OBS/audit?work_id=W-OBS")
    client.get("/api/scenario/SCN-OBS/audit?work_id=W-OBS")
    assert canonical_state_fingerprint(store["W-OBS"]) == fp_before
    assert store["W-OBS"].revision == rev_before
    # deterministic across reads (no new ids / volatile data)
    a = client.get("/api/scenario/SCN-OBS/audit?work_id=W-OBS").json()
    b = client.get("/api/scenario/SCN-OBS/audit?work_id=W-OBS").json()
    assert a == b


def test_audit_missing_scenario_fails_closed(app_and_store):
    client, _ = app_and_store
    r = client.get("/api/scenario/SCN-NOPE/audit")
    assert r.status_code == 404


def test_audit_survives_restart(app_and_store):
    # Build instance A, run pipeline, then a NEW WorkStore over the SAME work_dir + same scenario dir.
    with tempfile.TemporaryDirectory() as td:
        work_dir = tempfile.mkdtemp()
        scenario_dir = tempfile.mkdtemp()
        artifact_dir = os.path.join(td, "art")

        def mk(store):
            service = ScenarioService(repository=ScenarioRepository(scenario_dir), artifact_dir=artifact_dir)
            app = FastAPI()
            app.include_router(make_router(service, work_resolver=lambda wid: store.get(wid)), prefix="/api")
            return TestClient(app)

        storeA = WorkStore(work_dir)
        cA = mk(storeA)
        _run_pipeline(cA, storeA)

        # RESTART -> instance B (new store + new service/repo over the same dirs)
        storeB = WorkStore(work_dir)
        cB = mk(storeB)
        r = cB.get("/api/scenario/SCN-OBS/audit?work_id=W-OBS")
        assert r.status_code == 200
        a = r.json()
        assert a["work"]["linked_to_scenario"] is True
        assert {s["stage"]: s["status"] for s in a["stages"]}["EXECUTION"] == "RECORDED"
        assert a["execution"]["status"] == "SUCCEEDED"


def test_audit_work_without_predictive_content_still_valid(app_and_store):
    client, store = app_and_store
    store = store
    # a work WITHOUT predictive/prescriptive knowledge -> only PRJ-ACFL, no fabricated artifacts
    bare = CanonicalWorkState(work=EurekaWork(work_id="W-BARE", title="b", user_intent="u",
                                              task_category="c", problem_statement="p"))
    bare.acfl.weights = {"cost": 50.0, "risk": 50.0}
    store["W-BARE"] = bare
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-BARE", "work_id": "W-BARE",
                                              "assumptions": [{"delta": 0.1}]})
    r = client.get("/api/scenario/SCN-BARE/audit?work_id=W-BARE")
    assert r.status_code == 200
    ids = [x["artifact_id"] for x in r.json()["projected_artifacts"]]
    assert ids == ["PRJ-ACFL"]


def test_audit_work_id_identity_mismatch_is_derived(app_and_store):
    client, store = app_and_store
    _run_pipeline(client, store, sid="SCN-OBS")
    # a DIFFERENT work_id (not the source of SCN-OBS) -> WORK stage DERIVED (link does not match Q2)
    other = CanonicalWorkState(work=EurekaWork(work_id="W-OTHER", title="o", user_intent="u",
                                               task_category="c", problem_statement="p"))
    other.acfl.weights = {"cost": 70.0, "risk": 70.0}
    other.result = WorkResult(result_id="R2", work_id="W-OTHER", status="AVAILABLE", summary="x")
    store["W-OTHER"] = other
    r = client.get("/api/scenario/SCN-OBS/audit?work_id=W-OTHER")
    assert r.status_code == 200
    a = r.json()
    assert a["work"]["linked_to_scenario"] is False
    assert {s["stage"]: s["status"] for s in a["stages"]}["WORK"] == "DERIVED"
