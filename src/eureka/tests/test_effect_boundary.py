"""LS-SCN-03 — adversarial tests for the EffectBoundary + ExecutionPolicy (Q4).

These exercise the REAL boundary enforcement logic (not a mock): they prove fail-closed behaviour
for controlled/dry-run execution. The gate is the single enforcement point that any current or
future controlled context must pass (and it is wired into WorkRuntime._execute_step).
"""
import pytest
from src.eureka.universe.effect_policy import (
    EffectClass, ExecutionMode, BoundaryDecision, DryRunContext, CapabilityEffectClassifier,
    ExecutionPolicy, EffectBoundary, PolicyError, default_boundary,
)


def mkctx(cap, target="T", mode=ExecutionMode.NORMAL, auth=None, level=2, req=0):
    return DryRunContext(capability_id=cap, target=target, mode=mode,
                         authorization=auth, execution_level=level, required_execution_level=req)


@pytest.fixture
def boundary():
    return default_boundary()


def test_guarded_dump_json_blocks_dry_run(tmp_path, boundary):
    # A MUTATE persistence write in DRY_RUN must be blocked and NOT write the file.
    target = str(tmp_path / "frozen.json")
    from src.eureka.universe.effect_policy import guarded_dump_json, ExecutionMode, PolicyError
    with pytest.raises(PolicyError) as exc:
        guarded_dump_json(boundary, target, {"a": 1}, mode=ExecutionMode.DRY_RUN)
    assert exc.value.reason_code == "MUTATE_IN_DRY_RUN"
    import os
    assert not os.path.exists(target)  # the real effect never happened


def test_guarded_dump_json_allows_canonical_persistence_normal(tmp_path, boundary):
    # NORMAL canonical-runtime persistence (with the runtime's own auth token) still works.
    import os
    target = str(tmp_path / "state.json")
    from src.eureka.universe.effect_policy import guarded_dump_json, ExecutionMode, CANONICAL_PERSISTENCE_AUTH
    guarded_dump_json(boundary, target, {"revision": 2}, mode=ExecutionMode.NORMAL, authorization=CANONICAL_PERSISTENCE_AUTH)
    assert os.path.exists(target)
    import json
    with open(target) as f:
        assert json.load(f) == {"revision": 2}


def test_dispatch_protects_mutate_before_installer():
    # install_action is MUTATE -> blocked in dry-run BEFORE the installer handler is ever reached.
    from src.eureka.universe.work_runtime import WorkRuntime
    wr = WorkRuntime()
    wr._dry_run = True
    stub_state = type("S", (), {"conditions": []})()
    step = type("S", (), {"capability_id": "install_action", "target": "EM[INSTALLER]", "status": "READY", "provenance": []})()
    wr._execute_step(stub_state, step)
    assert step.status == "BLOCKED"
    assert stub_state.conditions and stub_state.conditions[-1].status == "BLOCKED"


def test_known_read_allowed_in_dry_run(boundary):
    v = boundary.authorize(mkctx("inspect_document", mode=ExecutionMode.DRY_RUN))
    assert v.decision == BoundaryDecision.ALLOW


def test_known_compute_allowed_in_dry_run(boundary):
    for cap in ["predict", "evaluate_alternatives", "frozen_knowledge.detect_delta"]:
        assert boundary.authorize(mkctx(cap, mode=ExecutionMode.DRY_RUN)).decision == BoundaryDecision.ALLOW


def test_simulate_allowed_in_dry_run(boundary):
    # execute_action is a simulated/observation capability
    v = boundary.authorize(mkctx("execute_action", mode=ExecutionMode.DRY_RUN))
    assert v.decision == BoundaryDecision.ALLOW


def test_mutate_blocked_in_dry_run(boundary):
    v = boundary.authorize(mkctx("install_action", mode=ExecutionMode.DRY_RUN))
    assert v.decision == BoundaryDecision.BLOCK
    assert v.reason_code == "MUTATE_IN_DRY_RUN"


def test_mutate_requires_authorization_normal(boundary):
    # NORMAL + MUTATE without authorization -> BLOCK (fail-closed)
    v = boundary.authorize(mkctx("install_action", auth=None))
    assert v.decision == BoundaryDecision.BLOCK
    assert v.reason_code == "MISSING_AUTHORIZATION"


def test_mutate_allowed_normal_with_authorization(boundary):
    v = boundary.authorize(mkctx("install_action", auth="AUTH-1"))
    assert v.decision == BoundaryDecision.ALLOW


def test_unknown_capability_blocks(boundary):
    v = boundary.authorize(mkctx("totally_unknown_capability", mode=ExecutionMode.DRY_RUN))
    assert v.decision == BoundaryDecision.BLOCK
    assert v.reason_code == "UNKNOWN_EFFECT"


def test_missing_target_blocks(boundary):
    v = boundary.authorize(mkctx("predict", target=""))
    assert v.decision == BoundaryDecision.BLOCK
    assert v.reason_code == "MISSING_TARGET"


def test_execution_level_insufficient_blocks(boundary):
    v = boundary.authorize(mkctx("predict", level=1, req=5))
    assert v.decision == BoundaryDecision.BLOCK
    assert v.reason_code == "EXECUTION_LEVEL_INSUFFICIENT"


def test_enforce_raises_on_block(boundary):
    with pytest.raises(PolicyError) as exc:
        boundary.enforce(mkctx("install_action", mode=ExecutionMode.DRY_RUN))
    assert exc.value.reason_code == "MUTATE_IN_DRY_RUN"


def test_execute_never_calls_handler_on_block():
    """THE core guarantee: the real handler is NOT invoked when the gate blocks."""
    called = {"n": 0}
    boundary = default_boundary()

    def handler():
        called["n"] += 1
        return "executed"

    # handler would be a MUTATE write; in dry-run the gate raises BEFORE the handler runs.
    with pytest.raises(PolicyError):
        boundary.execute(mkctx("install_action", mode=ExecutionMode.DRY_RUN), handler)
    assert called["n"] == 0


def test_execute_calls_handler_when_allowed():
    boundary = default_boundary()
    calls = []
    out = boundary.execute(mkctx("predict"), lambda: calls.append(1) or "ok")
    assert out == "ok"
    assert calls == [1]


def test_llm_intent_cannot_authorize_mutation(boundary):
    # Even if the caller passes an authorization string, in DRY_RUN a MUTATE capability still blocks.
    v = boundary.authorize(mkctx("install_action", mode=ExecutionMode.DRY_RUN, auth="LLM-claimed-auth"))
    assert v.decision == BoundaryDecision.BLOCK
    assert v.reason_code == "MUTATE_IN_DRY_RUN"


def test_dry_run_context_is_the_only_gate(boundary):
    # A NORMAL mutate with authorization is allowed (existing path); DRY_RUN always blocks mutate.
    assert boundary.authorize(mkctx("install_action", auth="AUTH-1")).decision == BoundaryDecision.ALLOW
    assert boundary.authorize(mkctx("install_action", mode=ExecutionMode.DRY_RUN, auth="AUTH-1")).decision == BoundaryDecision.BLOCK


def test_custom_classifier_unknown_blocks():
    b = EffectBoundary(CapabilityEffectClassifier({"savedb": EffectClass.MUTATE}))
    v = b.authorize(mkctx("savedb", mode=ExecutionMode.DRY_RUN))
    assert v.decision == BoundaryDecision.BLOCK
