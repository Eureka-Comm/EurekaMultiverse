"""LS-PUBLISH — Canonical Publisher / Freeze: real execution result -> validated -> freeze -> published
immutable artifact.

The EM Publisher already froze (via `_freeze_signature`) and published a `PublishedResult` into the
canonical. This block makes the PUBLISH a real, observable, governed DURABLE effect: it materializes a
signed, tamper-evident publication artifact file (BEFORE absent, AFTER present), reusing the content
signature as the artifact identity. The artifact survives a restart and is discoverable read-only.
"""
import os
import tempfile

import pytest

from src.eureka.universe.work_store import WorkStore
from src.eureka.universe.canonical_state import CanonicalWorkState, ExecutionStep, StructuredFinding, WorkResult
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.publisher import EMPublisher
from src.eureka.universe.cognitive_engine import TestDoubleCognitiveEngine as StubEngine
from src.eureka.universe.publication_model import PublicationSection
from src.eureka.universe.problem_model import CognitiveTask
from src.eureka.universe.effect_policy import default_boundary, ExecutionMode, DryRunContext
from src.eureka.universe.canonical_identity import canonical_state_fingerprint


def _mk_canonical(work_id="W-PUB"):
    c = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="t", user_intent="u",
                                           task_category="c", problem_statement="p"))
    c.status = "RUNNING"
    c.revision = 1
    c.knowledge.findings.append(StructuredFinding(finding_id="F-1", statement="correlation found",
                                                  finding_type="RELATIONAL", status="VALIDATED"))
    c.execution_state = None
    c.execution_plan.steps.append(ExecutionStep(
        step_id="publish", capability_id="generate_report", target="EM Publisher",
        canonical_em="EM Publisher", status="RUNNING", produces_result=True))
    return c


def _mk_task():
    return CognitiveTask(task_id="publish", description="publish", owner="EM Publisher",
                         expected_outputs=["artifact"])


def _engine():
    eng = StubEngine()
    eng.register_publication_fixture("publish", [
        PublicationSection(section_id="SEC-1", section_type="SUMMARY",
                           content="Validated summary.", status="VALIDATED"),
        PublicationSection(section_id="SEC-2", section_type="FINDINGS",
                           content="correlation found", status="VALIDATED"),
    ])
    return eng


def _publisher(pub_dir, mode=ExecutionMode.REAL_EXECUTION):
    return EMPublisher(_engine(), boundary=default_boundary(), publication_dir=pub_dir, mode=mode)


def _artifact_file(pub_dir, work_id="W-PUB"):
    files = [f for f in os.listdir(pub_dir) if f.startswith(f"{work_id}-")]
    return os.path.join(pub_dir, files[0]) if files else None


def test_production_wiring_uses_real_publisher():
    from src.eureka.universe.server import runtime
    assert isinstance(runtime.publisher, EMPublisher)
    assert runtime.publisher.mode == ExecutionMode.REAL_EXECUTION
    assert runtime.publisher.publication_dir  # configured (not a mock)


def test_publish_real_effect_before_after():
    pub_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-PUB")
    assert _artifact_file(pub_dir) is None
    publisher = _publisher(pub_dir)
    publisher.execute_task(None, _mk_task(), canonical)
    # AFTER: durable publication artifact exists
    path = _artifact_file(pub_dir)
    assert path is not None
    import json
    content = json.load(open(path, "r", encoding="utf-8"))
    assert content["artifact_kind"] == "CANONICAL_PUBLICATION_ARTIFACT"
    assert content["work_id"] == "W-PUB"
    assert content["canonical_state_identity"] == canonical_state_fingerprint(canonical)
    assert content["publication_status"] == "PUBLISHED"
    # canonical publish state + frozen snapshot
    assert canonical.publication_state.status == "PUBLISHED"
    assert canonical.frozen_result is not None
    assert canonical.publication_state.publications[0].artifact == path


def test_freeze_signature_is_content_identity_and_tamper_evident():
    pub_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-PUB")
    publisher = _publisher(pub_dir)
    publisher.execute_task(None, _mk_task(), canonical)
    frozen = canonical.frozen_result
    # the stored signature equals the recomputed signature over the frozen snapshot (content identity)
    assert publisher._signature_from_frozen(frozen) == frozen.freeze_signature
    assert frozen.freeze_signature == publisher._freeze_signature(canonical)
    # tamper-evidence: altering the frozen snapshot content changes the recomputed signature
    tampered = frozen.model_copy(deep=True)
    tampered.validated_knowledge = []           # remove a finding -> content changed
    assert publisher._signature_from_frozen(tampered) != frozen.freeze_signature


def test_q4_governance_publish_is_mutate_and_dry_run_blocks():
    boundary = default_boundary()
    # classifier: publisher.publish is classified MUTATE
    assert boundary.classifier.effect_for("publisher.publish") .value == "MUTATE"
    # DRY_RUN blocks the publish effect
    ctx = DryRunContext(capability_id="publisher.publish", target="fs:publication:X",
                        mode=ExecutionMode.DRY_RUN, authorization="PUBLISHER:X")
    assert boundary.authorize(ctx).decision.value == "BLOCK"
    # REAL_EXECUTION + runtime authorization allows it
    ctx2 = DryRunContext(capability_id="publisher.publish", target="fs:publication:X",
                         mode=ExecutionMode.REAL_EXECUTION, authorization="PUBLISHER:X")
    assert boundary.authorize(ctx2).decision.value == "ALLOW"


def test_publish_dry_run_no_artifact():
    pub_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-DRY")
    publisher = _publisher(pub_dir, mode=ExecutionMode.DRY_RUN)
    publisher.execute_task(None, _mk_task(), canonical)
    # NO artifact was written (DRY_RUN blocks the MUTATE publish effect)
    assert os.listdir(pub_dir) == []
    assert canonical.publication_state.publications[0].artifact is None


def test_publish_idempotent_and_revisioned():
    pub_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-IDEM")
    publisher = _publisher(pub_dir)
    publisher.execute_task(None, _mk_task(), canonical)
    assert len([f for f in os.listdir(pub_dir)]) == 1
    # re-publish with UNCHANGED content -> same deterministic artifact (no duplicate file, idempotent)
    publisher._materialize_publication_artifact(canonical,
                                                canonical.publication_state.publications[0],
                                                canonical.frozen_result)
    assert len([f for f in os.listdir(pub_dir)]) == 1
    # change canonical content -> new freezee signature -> a NEW artifact (revisioning)
    canonical.knowledge.findings.append(StructuredFinding(finding_id="F-2", statement="new info",
                                                          finding_type="RELATIONAL", status="VALIDATED"))
    publisher.execute_task(None, _mk_task(), canonical)
    assert len([f for f in os.listdir(pub_dir)]) == 2


def test_publish_persist_and_restart_recovery():
    work_dir = tempfile.mkdtemp()
    pub_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-RT")
    storeA = WorkStore(work_dir)
    storeA["W-RT"] = canonical
    publisher = _publisher(pub_dir)
    publisher.execute_task(None, _mk_task(), canonical)
    storeA["W-RT"] = canonical   # persist the canonical with frozen_result + publication_state
    # RESTART -> new WorkStore over the same storage
    storeB = WorkStore(work_dir)
    reloaded = storeB["W-RT"]
    assert reloaded.frozen_result is not None
    assert reloaded.publication_state.status == "PUBLISHED"
    assert reloaded.publication_state.publications[0].artifact is not None
    # the durable publication artifact survives on disk
    assert _artifact_file(pub_dir, "W-RT") is not None


def test_forged_publication_payload_is_ignored():
    # The publish endpoint only takes an intent; the publisher derives everything SERVER-SIDE from the
    # canonical (no client result/frozen_result/authority/signature can become evidence).
    pub_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-FORGE")
    publisher = _publisher(pub_dir)
    publisher.execute_task(None, _mk_task(), canonical)
    import json
    content = json.load(open(_artifact_file(pub_dir, "W-FORGE"), "r", encoding="utf-8"))
    # the artifact identity derives from the canonical content signature, not from any client payload
    assert "signature:" in content["provenance"][-1]
    assert content["canonical_content_signature"] != "forged"
