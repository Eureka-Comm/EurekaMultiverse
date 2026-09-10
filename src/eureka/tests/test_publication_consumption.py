"""LS-PUBCONSUME — Read-only, VERIFIED Published Artifact Consumption.

Consuming means reading the durable publication evidence and VERIFYING it (schema + integrity via the
reused `_freeze_signature`/`_signature_from_frozen` + currentness), WITHOUT mutating anything and WITHOUT
treating it as a new canonical authority. ``release`` is intentionally OPEN: the repository defines no
real release/deliver/ship contract, so an invented ``status=RELEASED`` would be an artificial authority.
"""
import json
import os
import tempfile

import pytest

from src.eureka.universe.work_store import WorkStore
from src.eureka.universe.canonical_state import CanonicalWorkState, ExecutionStep, StructuredFinding
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.publisher import EMPublisher
from src.eureka.universe.cognitive_engine import TestDoubleCognitiveEngine as StubEngine
from src.eureka.universe.publication_model import PublicationSection
from src.eureka.universe.problem_model import CognitiveTask
from src.eureka.universe.effect_policy import default_boundary, ExecutionMode
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.publication_consumption import build_publication_consumption, verify_publication


def _mk_canonical(work_id="W-C"):
    c = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="t", user_intent="u",
                                           task_category="c", problem_statement="p"))
    c.status = "RUNNING"
    c.revision = 1
    c.knowledge.findings.append(StructuredFinding(finding_id="F-1", statement="correlation found",
                                                  finding_type="RELATIONAL", status="VALIDATED"))
    c.execution_plan.steps.append(ExecutionStep(step_id="publish", capability_id="generate_report",
                                                target="EM Publisher", canonical_em="EM Publisher",
                                                status="RUNNING", produces_result=True))
    return c


def _mk_task():
    return CognitiveTask(task_id="publish", description="publish", owner="EM Publisher")


def _engine():
    eng = StubEngine()
    eng.register_publication_fixture("publish", [
        PublicationSection(section_id="SEC-1", section_type="SUMMARY", content="Validated summary.",
                           status="VALIDATED")])
    return eng


def _publish(work_id="W-C"):
    pub_dir = tempfile.mkdtemp()
    work_dir = tempfile.mkdtemp()
    store = WorkStore(work_dir)
    canonical = _mk_canonical(work_id)
    store[work_id] = canonical
    publisher = EMPublisher(_engine(), boundary=default_boundary(), publication_dir=pub_dir,
                            mode=ExecutionMode.REAL_EXECUTION)
    publisher.execute_task(None, _mk_task(), canonical)
    store[work_id] = canonical
    return store, publisher, pub_dir, canonical


def _artifact_path(pub_dir, work_id="W-C"):
    files = [f for f in os.listdir(pub_dir) if f.startswith(f"{work_id}-")]
    return os.path.join(pub_dir, files[0]) if files else None


def test_valid_consumption_verified():
    store, publisher, pub_dir, canonical = _publish("W-C")
    result = build_publication_consumption(store, publisher, "W-C")
    assert result["publication"] is not None
    assert result["verification"]["schema_valid"] is True
    assert result["verification"]["integrity"] == "VALID"
    assert result["verification"]["currentness"] == "CURRENT"
    assert result["verification"]["signature_match"] is True


def test_tampered_artifact_detected():
    store, publisher, pub_dir, canonical = _publish("W-C")
    # tamper with the artifact content (change the frozen knowledge)
    path = _artifact_path(pub_dir)
    artifact = json.load(open(path, "r", encoding="utf-8"))
    artifact["frozen_result"]["validated_knowledge"] = []
    json.dump(artifact, open(path, "w", encoding="utf-8"))
    result = build_publication_consumption(store, publisher, "W-C")
    assert result["verification"]["integrity"] == "TAMPERED"
    assert result["verification"]["signature_match"] is False


def test_missing_artifact_consumption():
    store, publisher, pub_dir, canonical = _publish("W-C")
    # a different work with no publication
    empty = CanonicalWorkState(work=EurekaWork(work_id="W-EMPTY", title="t", user_intent="u",
                                               task_category="c", problem_statement="p"))
    store["W-EMPTY"] = empty
    result = build_publication_consumption(store, publisher, "W-EMPTY")
    assert result["publication"] is None
    assert result["verification"]["integrity"] == "MISSING"


def test_historical_artifact_not_corrupted():
    store, publisher, pub_dir, canonical = _publish("W-H")
    # the canonical Work changes AFTER publication (a new finding, Q2-relevant)
    canonical.knowledge.findings.append(StructuredFinding(finding_id="F-2", statement="new info",
                                                          finding_type="RELATIONAL", status="VALIDATED"))
    store["W-H"] = canonical
    result = build_publication_consumption(store, publisher, "W-H")
    # the artifact is internally VALID (its signature over its own frozen snapshot) but HISTORICAL
    assert result["verification"]["integrity"] == "VALID"
    assert result["verification"]["currentness"] == "HISTORICAL"


def test_consumption_is_read_only_and_immutable():
    store, publisher, pub_dir, canonical = _publish("W-I")
    fp_before = canonical_state_fingerprint(canonical)
    rev_before = canonical.revision
    r1 = build_publication_consumption(store, publisher, "W-I")
    r2 = build_publication_consumption(store, publisher, "W-I")
    assert r1 == r2                       # deterministic read (no new ids / no volatile data)
    assert canonical_state_fingerprint(store["W-I"]) == fp_before
    assert store["W-I"].revision == rev_before


def test_path_traversal_fails_closed():
    store, publisher, pub_dir, canonical = _publish("W-C")
    with pytest.raises(ValueError):
        build_publication_consumption(store, publisher, "../../etc/passwd")


def test_corrupt_artifact_fails_closed():
    store, publisher, pub_dir, canonical = _publish("W-C")
    path = _artifact_path(pub_dir)
    with open(path, "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    result = build_publication_consumption(store, publisher, "W-C")
    assert result["publication"] is None
    assert result["verification"]["integrity"] == "TAMPERED"


def test_release_contract_is_open_not_invented():
    # Forensic: EUREKA defines NO real release / deliver / ship / deploy contract. We deliberately do NOT
    # fabricate a 'release' boundary (an invented status=RELEASED would be an artificial authority).
    # Concrete, checkable facts: (1) the publication schema has no release status; (2) no ReleaseAuthority
    # / ReleaseService mechanism exists; (3) consumption is read-only (no release function).
    from src.eureka.universe import publication_model, publication_consumption
    pub_model = open(publication_model.__file__, encoding="utf-8").read()
    assert "release" not in pub_model.lower()
    consumption_src = open(publication_consumption.__file__, encoding="utf-8").read()
    assert "def release" not in consumption_src
    assert "release_authority" not in consumption_src.lower()
    # the exposed API surface is READ-ONLY verification (no release mutation)
    assert "def build_publication_consumption" in consumption_src
    assert "def verify_publication" in consumption_src
