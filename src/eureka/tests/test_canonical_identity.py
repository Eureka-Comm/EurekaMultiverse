"""LS-Q2 — canonical source-state identity tests (canonical_identity.py)."""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, WorkResult
from src.eureka.universe.canonical_identity import canonical_state_fingerprint, compare_source_identity


def mk(work_id="W1", with_result=False, revision=1):
    state = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="t", user_intent="u", task_category="c", problem_statement="p"))
    state.revision = revision
    if with_result:
        state.result = WorkResult(result_id="RES-1", work_id=work_id, status="AVAILABLE",
                                  summary="done", recommendations=["rec-1"])
    return state


def test_same_content_same_fingerprint():
    s = mk()
    assert canonical_state_fingerprint(s) == canonical_state_fingerprint(s)


def test_changed_semantic_content_different_fingerprint():
    a = mk(with_result=False)
    b = mk(with_result=True)
    assert canonical_state_fingerprint(a) != canonical_state_fingerprint(b)


def test_work_id_change_same_fingerprint():
    # content identity excludes work_id (work identity, not content)
    a = mk(work_id="W1", with_result=True)
    b = mk(work_id="W2", with_result=True)
    assert canonical_state_fingerprint(a) == canonical_state_fingerprint(b)


def test_revision_change_same_fingerprint():
    # content identity excludes revision (version counter, not content)
    a = mk(revision=1, with_result=True)
    b = mk(revision=99, with_result=True)
    assert canonical_state_fingerprint(a) == canonical_state_fingerprint(b)


def test_fingerprint_does_not_mutate_state():
    s = mk(with_result=True)
    before_rev = s.revision
    before_work = s.work.work_id
    fingerprint = canonical_state_fingerprint(s)
    assert s.revision == before_rev
    assert s.work.work_id == before_work
    assert len(fingerprint) == 64


def test_persist_reload_same_fingerprint():
    s = mk(with_result=True)
    dumped = s.model_dump(mode="json")
    reloaded = CanonicalWorkState.model_validate(dumped)
    assert canonical_state_fingerprint(s) == canonical_state_fingerprint(reloaded)


def test_stale_detection():
    a = mk(with_result=False)
    fp_a = canonical_state_fingerprint(a)
    assert compare_source_identity(fp_a, a) == "MATCH"
    b = mk(with_result=True)
    assert compare_source_identity(fp_a, b) == "STALE"
    assert compare_source_identity(None, a) == "STALE"


def test_deterministic_across_processes_like_rebuild():
    # two independently-constructed equivalent states produce the same fingerprint
    a = mk(with_result=True)
    b = mk(with_result=True)
    assert canonical_state_fingerprint(a) == canonical_state_fingerprint(b)
