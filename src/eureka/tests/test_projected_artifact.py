"""LS-Q3 — Projected Artifact Authority tests (projected_artifact.py)."""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.projected_artifact import (
    ProjectedArtifact, ArtifactScope, AuthorityClass, CanonicalStatus,
)


def mk(work_id="W1", with_result=False):
    state = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="t", user_intent="u", task_category="c", problem_statement="p"))
    if with_result:
        from src.eureka.universe.canonical_state import WorkResult
        state.result = WorkResult(result_id="RES-1", work_id=work_id, status="AVAILABLE", summary="done")
    return state


def test_create_projected_artifact():
    s = mk(with_result=True)
    a = ProjectedArtifact.from_source("PRJ-1", "RESULT", s)
    assert a.is_non_canonical is True
    assert a.scope == ArtifactScope.SCENARIO
    assert a.authority == AuthorityClass.PROJECTED
    assert a.canonical_status == CanonicalStatus.NON_CANONICAL


def test_source_identity_reuses_q2():
    s = mk(with_result=True)
    a = ProjectedArtifact.from_source("PRJ-1", "RESULT", s)
    assert a.source_state_identity == canonical_state_fingerprint(s)


def test_same_source_same_identity():
    s = mk(with_result=True)
    a1 = ProjectedArtifact.from_source("PRJ-1", "RESULT", s)
    a2 = ProjectedArtifact.from_source("PRJ-2", "RESULT", s)
    assert a1.source_state_identity == a2.source_state_identity


def test_stale_source_detectable():
    s = mk(with_result=False)
    a = ProjectedArtifact.from_source("PRJ-1", "PREDICTION", s)
    assert a.verify_source(s) == "MATCH"
    changed = mk(with_result=True)
    assert a.verify_source(changed) == "STALE"


def test_projected_cannot_be_canonical_implicitly():
    with pytest.raises(ValueError):
        ProjectedArtifact(artifact_id="x", artifact_kind="R", scope=ArtifactScope.CANONICAL,
                          source_state_identity="h", provenance=["p"])


def test_projected_cannot_carry_authoritative_authority():
    for auth in (AuthorityClass.CANONICAL, AuthorityClass.RESULT,
                 AuthorityClass.RECOMMENDATION, AuthorityClass.HUMAN_DECISION):
        with pytest.raises(ValueError):
            ProjectedArtifact(artifact_id="x", artifact_kind="R", authority=auth,
                              source_state_identity="h", provenance=["p"])


def test_projected_cannot_be_canonical_status():
    with pytest.raises(ValueError):
        ProjectedArtifact(artifact_id="x", artifact_kind="R",
                          canonical_status=CanonicalStatus.CANONICAL,
                          source_state_identity="h", provenance=["p"])


def test_missing_provenance_rejected():
    with pytest.raises(ValueError):
        ProjectedArtifact(artifact_id="x", artifact_kind="R",
                          source_state_identity="h", provenance=[])


def test_missing_source_identity_rejected():
    with pytest.raises(ValueError):
        ProjectedArtifact(artifact_id="x", artifact_kind="R", provenance=["p"], source_state_identity="")


def test_serialization_roundtrip_preserves_governance():
    s = mk(with_result=True)
    a = ProjectedArtifact.from_source("PRJ-1", "PREDICTION", s)
    dumped = a.model_dump(mode="json")
    reloaded = ProjectedArtifact.model_validate(dumped)
    assert reloaded.scope == ArtifactScope.SCENARIO
    assert reloaded.authority == AuthorityClass.PROJECTED
    assert reloaded.provenance == a.provenance
    assert reloaded.source_state_identity == a.source_state_identity
    assert reloaded.canonical_status == CanonicalStatus.NON_CANONICAL


def test_canonical_state_unchanged_after_creation_and_validation():
    s = mk(with_result=True)
    fp_before = canonical_state_fingerprint(s)
    a = ProjectedArtifact.from_source("PRJ-1", "RESULT", s)
    ProjectedArtifact.model_validate(a.model_dump(mode="json"))
    assert canonical_state_fingerprint(s) == fp_before
    assert s.revision == 1  # untouched


def test_malicious_canonical_flag_rejected():
    # a manual/manual attempt to construct an artifact as canonical is rejected
    with pytest.raises(ValueError):
        ProjectedArtifact.model_validate({
            "artifact_id": "x", "artifact_kind": "RESULT",
            "scope": "CANONICAL", "authority": "RESULT", "provenance": ["p"],
            "source_state_identity": "h", "canonical_status": "CANONICAL", "payload": {},
        })


def test_llm_cannot_elevate_authority():
    # even if generated content claims canonical authority, construction is rejected
    with pytest.raises(ValueError):
        ProjectedArtifact(artifact_id="x", artifact_kind="RESULT", authority=AuthorityClass.CANONICAL,
                          source_state_identity="h", provenance=["llm-generated"])
