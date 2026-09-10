"""LS-WORKOBS — Canonical work observability (READ-ONLY): Work → Execution → Result → Publish → Consumption.

The projection composes the existing authorities (WorkStore + EM Publisher + publication consumption)
so a human can reconstruct the canonical chain. It never mutates; a TAMPERED artifact is an integrity
failure; a HISTORICAL artifact is VALID historical evidence (never corrupted); read-only GETs leave the
canonical fingerprint / revision unchanged. Restart-safe.
"""
import json
import os
import tempfile

import pytest

from src.eureka.universe.work_store import WorkStore
from src.eureka.universe.canonical_state import (CanonicalWorkState, ExecutionStep, StructuredFinding,
                                                 RuntimeCallMetadata, EMStatus)
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.installation_model import ExecutionState, ExecutionRequest, ExecutionResult
from src.eureka.universe.publisher import EMPublisher
from src.eureka.universe.cognitive_engine import TestDoubleCognitiveEngine as StubEngine
from src.eureka.universe.publication_model import PublicationSection
from src.eureka.universe.problem_model import CognitiveTask
from src.eureka.universe.effect_policy import default_boundary, ExecutionMode
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.work_observability import build_work_audit


def _mk_canonical(work_id="W-OBS"):
    c = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="t", user_intent="u",
                                           task_category="c", problem_statement="p"))
    c.status = "RUNNING"
    c.revision = 1
    c.knowledge.findings.append(StructuredFinding(finding_id="F-1", statement="correlation found",
                                                  finding_type="RELATIONAL", status="VALIDATED"))
    c.execution_state = ExecutionState(
        state_id="EXEC-1", action_plan_ref="AP-1", status="COMPLETED",
        request=ExecutionRequest(request_id="REQ-1", action_plan_ref="AP-1",
                                 target_execution_level=1, requested_by="t"),
        result=ExecutionResult(result_id="RES-1", request_ref="REQ-1", status="SUCCEEDED",
                               successful_actions=["A1"]))
    c.execution_plan.steps.append(ExecutionStep(step_id="publish", capability_id="generate_report",
                                                target="EM Publisher", canonical_em="EM Publisher",
                                                status="RUNNING", produces_result=True))
    # COGNITIVE observatory data (real canonical state): EM pipeline statuses + DeepSeek/ACFL trace
    c.em_pipeline.append(EMStatus(canonical_em="EM Core", status="COMPLETED", step_ids=["t1"]))
    c.em_pipeline.append(EMStatus(canonical_em="EM Predictor", status="COMPLETED", step_ids=["t3"]))
    c.runtime_metadata.append(RuntimeCallMetadata(call_id="CALL-1", em="EM Core", capability_id="propose_problem",
                                                  model="deepseek-chat", status="COMPLETED", latency_ms=1234.5))
    c.runtime_metadata.append(RuntimeCallMetadata(call_id="CALL-2", em="EM Predictor", capability_id="propose_predictions",
                                                  model="ACFL_DETERMINISTIC", status="COMPLETED", latency_ms=0.7))
    return c


def _mk_task():
    return CognitiveTask(task_id="publish", description="publish", owner="EM Publisher")


def _engine():
    eng = StubEngine()
    eng.register_publication_fixture("publish", [
        PublicationSection(section_id="SEC-1", section_type="SUMMARY", content="Validated summary.",
                           status="VALIDATED")])
    return eng


def _setup(work_id="W-OBS"):
    work_dir = tempfile.mkdtemp()
    pub_dir = tempfile.mkdtemp()
    store = WorkStore(work_dir)
    canonical = _mk_canonical(work_id)
    store[work_id] = canonical
    publisher = EMPublisher(_engine(), boundary=default_boundary(), publication_dir=pub_dir,
                            mode=ExecutionMode.REAL_EXECUTION)
    publisher.execute_task(None, _mk_task(), canonical)
    store[work_id] = canonical
    return store, publisher, pub_dir, canonical


def test_canonical_chain_is_observable():
    store, publisher, pub_dir, canonical = _setup("W-OBS")
    audit = build_work_audit(store, publisher, "W-OBS")
    stages = {s.stage: s.status for s in audit.stages}
    assert stages["WORK"] == "RECORDED"
    assert stages["EXECUTION"] == "RECORDED"
    assert stages["RESULT"] == "RECORDED"
    assert stages["PUBLISH"] == "RECORDED"
    assert stages["CONSUMPTION"] == "RECORDED"
    assert audit.canonical_state_identity == canonical_state_fingerprint(canonical)
    assert audit.execution["result"]["status"] == "SUCCEEDED"
    assert audit.publication["publication_state"]["status"] == "PUBLISHED"
    assert audit.consumption["verification"]["integrity"] == "VALID"
    assert audit.consumption["verification"]["currentness"] == "CURRENT"
    # COGNITIVE observatory: contractual pipeline + observed EM statuses + DeepSeek/ACFL trace
    assert audit.contractual_pipeline == ["EM Core", "EM Structurer", "EM Descriptor", "EM Predictor",
                                          "EM Prescriptor", "EM Actioner", "EM Installer", "EM Publisher"]
    observed = {e["canonical_em"]: e["status"] for e in audit.em_pipeline}
    assert observed["EM Core"] == "COMPLETED"
    assert observed["EM Predictor"] == "COMPLETED"
    models = {t["em"]: t["model"] for t in audit.cognitive_trace}
    assert models["EM Core"] == "deepseek-chat"               # real DeepSeek proposal
    assert models["EM Predictor"] == "ACFL_DETERMINISTIC"     # deterministic math, not LLM


def test_consumption_is_non_authoritative_and_read_only():
    store, publisher, pub_dir, canonical = _setup("W-IMM")
    fp_before = canonical_state_fingerprint(canonical)
    rev_before = canonical.revision
    a1 = build_work_audit(store, publisher, "W-IMM")
    a2 = build_work_audit(store, publisher, "W-IMM")
    assert a1 == a2                      # deterministic read (no volatile ids / data)
    assert canonical_state_fingerprint(store["W-IMM"]) == fp_before
    assert store["W-IMM"].revision == rev_before


def test_historical_artifact_is_valid_not_corrupted():
    store, publisher, pub_dir, canonical = _setup("W-H")
    canonical.knowledge.findings.append(StructuredFinding(finding_id="F-2", statement="new info",
                                                          finding_type="RELATIONAL", status="VALIDATED"))
    store["W-H"] = canonical
    audit = build_work_audit(store, publisher, "W-H")
    v = audit.consumption["verification"]
    assert v["integrity"] == "VALID"        # internally valid snapshot
    assert v["currentness"] == "HISTORICAL" # but an earlier version of the Work
    assert v["signature_match"] is True


def test_tampered_artifact_reported_as_integrity_failure():
    store, publisher, pub_dir, canonical = _setup("W-T")
    path = sorted(os.path.join(pub_dir, f) for f in os.listdir(pub_dir))[0]
    artifact = json.load(open(path, "r", encoding="utf-8"))
    artifact["frozen_result"]["validated_knowledge"] = []
    json.dump(artifact, open(path, "w", encoding="utf-8"))
    audit = build_work_audit(store, publisher, "W-T")
    assert audit.consumption["verification"]["integrity"] == "TAMPERED"
    assert audit.consumption["verification"]["signature_match"] is False


def test_unknown_work_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        store = WorkStore(td)
        with pytest.raises(ValueError):
            build_work_audit(store, EMPublisher(_engine(), boundary=default_boundary(),
                                                publication_dir=tempfile.mkdtemp()), "W-NOPE")


def test_corrupt_work_reported_as_corrupt_not_crash():
    # A WorkStore record that fails schema validation must be reported honestly (fail-closed), NOT
    # silently treated as absent nor crash the observatory. CONSTELACIÓN must remain read-only & alive.
    with tempfile.TemporaryDirectory() as td:
        store = WorkStore(td)
        with open(os.path.join(td, "W-CORRUPT.json"), "w", encoding="utf-8") as f:
            json.dump({"work": {"work_id": "W-CORRUPT"}, "status": None}, f)   # invalid: status must be str
        audit = build_work_audit(store, EMPublisher(_engine(), boundary=default_boundary(),
                                                    publication_dir=tempfile.mkdtemp()), "W-CORRUPT")
        assert audit.status == "CORRUPT"
        assert audit.stages[0].stage == "WORK" and audit.stages[0].status == "NOT_RECORDED"
        assert audit.contractual_pipeline == []   # no fabricated pipeline for a corrupt work


def test_work_audit_survives_restart():
    # publish in instance A, then a NEW store over the same work storage -> same canonical evidence.
    work_dir = tempfile.mkdtemp()
    pub_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-RT")
    storeA = WorkStore(work_dir)
    storeA["W-RT"] = canonical
    publisherA = EMPublisher(_engine(), boundary=default_boundary(), publication_dir=pub_dir,
                             mode=ExecutionMode.REAL_EXECUTION)
    publisherA.execute_task(None, _mk_task(), canonical)
    storeA["W-RT"] = canonical
    # RESTART -> instance B
    storeB = WorkStore(work_dir)
    publisherB = EMPublisher(_engine(), boundary=default_boundary(), publication_dir=pub_dir,
                             mode=ExecutionMode.REAL_EXECUTION)
    audit = build_work_audit(storeB, publisherB, "W-RT")
    assert audit.execution["result"]["status"] == "SUCCEEDED"
    assert audit.publication["publication_state"]["status"] == "PUBLISHED"
    assert audit.consumption["verification"]["integrity"] == "VALID"
    assert audit.consumption["verification"]["currentness"] == "CURRENT"
