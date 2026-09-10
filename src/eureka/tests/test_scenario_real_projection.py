"""LS-SCN-RPRED — REAL predictive + prescriptive WHAT-IF projection (multi-metric, DRY_RUN).

The WHAT-IF now reads the canonical work's REAL predictive_knowledge and prescriptive_knowledge and
projects them (with the REAL ACFL engine) into a ProjectedArtifact. This proves the real path:
ScenarioRuntime -> EMPredictor AST/ACFLEngine -> ProjectedArtifact, WITHOUT mutating the canonical and
with assumptions genuinely affecting the real ACFL computation. No fabrications, no hidden fallback.
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

_WORK_STORE = WorkStore(tempfile.mkdtemp())


def _mk_real_with_knowledge(work_id="W-PRED"):
    real = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="Real Work", user_intent="analyze dataset",
        task_category="DESCRIPTOR", problem_statement="Analyze dataset X"))
    real.knowledge.findings.append(StructuredFinding(finding_id="F-1", statement="correlation found",
                                                     finding_type="RELATIONAL", evidence_refs=["EVI-1"]))
    real.result = WorkResult(result_id="R-1", work_id=work_id, summary="done",
                             status="AVAILABLE", confidence=0.9)
    real.acfl.weights = {"cost": 50.0, "risk": 50.0}
    # REAL predictive knowledge (as the EMPredictor produces: GCLV predicate over a numeric variable)
    real.predictive_knowledge.predicates.append(PredictivePredicate(
        predicate_id="PP-1", target="revenue",
        logical_structure=GCLVMembership(input=Variable(name="revenue"), alpha=1.0, gamma=0.5, m=0.5),
        mse=0.0123, status="VALIDATED", provenance=["ACFL_ENGINE_V5.1"]))
    real.predictive_knowledge.predictions.append(PredictionKnowledge(
        prediction_id="PRED-1", target_variable="revenue", predicted_value=0.7,
        model_type="ACFL_ENGINE", model_definition="MSE=0.0123", validation_status="VALIDATED",
        predictor_variables=["revenue"], uncertainty=PredictiveUncertainty(status="NOT_AVAILABLE"),
        provenance=["Task[t_pred]"]))
    real.predictive_knowledge.status = "FROZEN"
    # REAL prescriptive knowledge (as the EMPrescriptor produces)
    alt1 = PrescriptionAlternative(alternative_id="ALT-1", description="increase spend", score=0.8)
    alt2 = PrescriptionAlternative(alternative_id="ALT-2", description="hold", score=0.5)
    real.prescriptive_knowledge.prescriptions.append(ValidatedPrescription(
        prescription_id="PRES-1", objective="maximize revenue", alternatives=[alt1, alt2],
        applicable_criteria=[], constraints=[], decision_rule=DecisionRule(status="DOCUMENTED"),
        supporting_predictions=["PRED-1"], supporting_knowledge=[], rationale="r",
        authority="HUMAN", provenance=["EMPrescriptor"], validation_status="EVALUATED",
        selected_alternative=alt1))
    real.prescriptive_knowledge.status = "FROZEN"
    _WORK_STORE[work_id] = real
    return real


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as td:
        service = ScenarioService(repository=ScenarioRepository(td), artifact_dir=os.path.join(td, "art"))
        app = FastAPI()
        app.include_router(make_router(service, work_resolver=lambda wid: _WORK_STORE.get(wid)), prefix="/api")
        yield TestClient(app)


def _projected(client, sid, delta, work_id="W-PRED"):
    r = client.post("/api/scenario/whatif", json={"scenario_id": sid, "work_id": work_id,
                                                   "assumptions": [{"delta": delta}]})
    assert r.status_code == 200
    return r.json()


def test_real_predictive_and_prescriptive_evidence_projected(client):
    _mk_real_with_knowledge()
    body = _projected(client, "SCN-RP", 0.1)
    assert body["scope"] == "SCENARIO"
    assert body["authority"] == "PROJECTED"
    assert body["canonical_status"] == "NON_CANONICAL"
    arts = {a["artifact_id"]: a for a in body["projected_artifacts"]}
    # real ACFL metric present
    assert "PRJ-ACFL" in arts
    assert "gclv" in arts["PRJ-ACFL"]["payload"]
    # real predictive evidence (predicted_value + MSE + ACFL projection via REAL engine)
    assert "PRJ-PREDICTIVE" in arts
    pred = arts["PRJ-PREDICTIVE"]["payload"]["predictions"][0]
    assert pred["target"] == "revenue"
    assert pred["predicted_value"] == 0.7
    assert pred["mse"] == 0.0123
    assert pred["model"] == "ACFL_ENGINE"
    assert "acfl_projection" in pred and pred["acfl_projection"]["variable"] == "revenue"
    # real prescriptive evidence (objectives, alternatives with real score, authority)
    assert "PRJ-PRESCRIPTIVE" in arts
    presc = arts["PRJ-PRESCRIPTIVE"]["payload"]["prescriptions"][0]
    assert presc["objective"] == "maximize revenue"
    assert presc["selected_alternative"]["alternative_id"] == "ALT-1"
    assert presc["alternatives"][0]["score"] == 0.8
    assert presc["authority"] == "HUMAN"
    assert presc["validation_status"] == "EVALUATED"


def test_assumption_delta_changes_real_acfl_projection(client):
    _mk_real_with_knowledge()
    a = _projected(client, "SCN-A", 0.1)
    b = _projected(client, "SCN-B", 0.2)
    aA = {x["artifact_id"]: x["payload"] for x in a["projected_artifacts"]}
    bA = {x["artifact_id"]: x["payload"] for x in b["projected_artifacts"]}
    assert aA["PRJ-ACFL"]["m"] != bA["PRJ-ACFL"]["m"]          # delta -> real ACFL m
    assert aA["PRJ-ACFL"]["gclv"] != bA["PRJ-ACFL"]["gclv"]    # delta -> real gclv
    # the real per-prediction ACFL projection also responds to the assumption (real, not fabricated)
    pa = aA["PRJ-PREDICTIVE"]["predictions"][0]["acfl_projection"]["acfl_projected"]
    pb = bA["PRJ-PREDICTIVE"]["predictions"][0]["acfl_projection"]["acfl_projected"]
    assert pa != pb


def test_projection_is_deterministic(client):
    _mk_real_with_knowledge()
    a = _projected(client, "SCN-D1", 0.1)
    b = _projected(client, "SCN-D1", 0.1)
    assert a["projected_artifacts"] == b["projected_artifacts"]


def test_canonical_immutable_across_whatif(client):
    real = _mk_real_with_knowledge()
    fp_before = canonical_state_fingerprint(real)
    rev_before = real.revision
    for delta in (0.1, 0.2, -0.05):
        _projected(client, f"SCN-{delta}", delta)
    assert canonical_state_fingerprint(real) == fp_before
    assert real.revision == rev_before


def test_source_mutation_detected_as_incomparable_in_compare(client):
    # A FRESH WHAT-IF always snapshots the current canonical source (it is never stale vs itself).
    # The stale gate for the WHAT-IF pipeline is the SOURCE-IDENTITY comparison: two projected
    # scenarios from DIFFERENT canonical source identities are incomparable (fail-closed 409).
    real = _mk_real_with_knowledge()
    _projected(client, "SCN-V1", 0.1)                       # binds to source identity I0
    real.knowledge.findings.append(StructuredFinding(finding_id="F-2", statement="new info",
                                                     finding_type="RELATIONAL"))   # mutate (Q2-relevant)
    _projected(client, "SCN-V2", 0.1)                       # binds to NEW source identity I1
    r = client.post("/api/scenario/compare", json={"scenario_ids": ["SCN-V1", "SCN-V2"],
                                                   "baseline_scenario_id": "SCN-V1"})
    assert r.status_code == 409
    assert "INCOMPARABLE_SOURCE_STATE" in r.json()["detail"]["error"]


def test_authority_forgery_is_ignored(client):
    _mk_real_with_knowledge()
    r = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-FORGE", "work_id": "W-PRED",
                                                   "assumptions": [{"delta": 0.1}],
                                                   "authority": "CANONICAL", "scope": "CANONICAL",
                                                   "canonical_status": "CANONICAL"})
    assert r.status_code == 200
    body = r.json()
    assert body["authority"] == "PROJECTED"
    assert body["scope"] == "SCENARIO"
    assert body["canonical_status"] == "NON_CANONICAL"


def test_execution_forgery_stays_dry_run(client):
    _mk_real_with_knowledge()
    r = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-X", "work_id": "W-PRED",
                                                   "assumptions": [{"delta": 0.1}],
                                                   "execute": True, "promote": True,
                                                   "bypass_governance": True, "execution_mode": "REAL"})
    assert r.status_code == 200
    body = r.json()
    # WHAT-IF only produces projected artifacts; there is no execution/real-effect and no promote
    for banned in ("execute", "promote", "REAL_EXECUTION", "bypass_governance"):
        assert banned not in body
    assert all(a["authority"] == "PROJECTED" for a in body["projected_artifacts"])


def test_legacy_bare_work_only_acfl_metric(client):
    # A bare work (no predictive/prescriptive content) falls back to ACFL-only projection (honest:
    # there is no REAL prediction to surface, so no PRJ-PREDICTIVE / PRJ-PRESCRIPTIVE is fabricated).
    _mk_real_with_knowledge("W-PRED")
    BARE = {"work_id": "W-BARE", "title": "t", "user_intent": "u", "task_category": "c",
            "problem_statement": "p", "acfl_weights": {"cost": 50.0, "risk": 50.0}}
    r = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-BARE", "work": BARE,
                                                   "assumptions": [{"delta": 0.1}]})
    assert r.status_code == 200
    assert r.json()["authority"] == "PROJECTED"
    ids = [a["artifact_id"] for a in r.json()["projected_artifacts"]]
    assert ids == ["PRJ-ACFL"]   # only the real ACFL metric; no fabricated predictive/prescriptive


def test_comparison_of_real_projection_scenarios(client):
    _mk_real_with_knowledge()
    for sid, delta in (("SCN-C0", 0.0), ("SCN-C1", 0.1), ("SCN-C2", 0.2)):
        _projected(client, sid, delta)
    r = client.post("/api/scenario/compare", json={"scenario_ids": ["SCN-C0", "SCN-C1", "SCN-C2"],
                                                   "baseline_scenario_id": "SCN-C0"})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "SCENARIO"
    assert body["authority"] == "PROJECTED"
    assert body["scenario_ids"] == ["SCN-C0", "SCN-C1", "SCN-C2"]
    for banned in ("best_scenario", "winner", "recommendation", "promote"):
        assert banned not in body
