"""LS-WORKEXEC — CANONICAL work governed REAL execution (production executor).

The canonical Work execution path previously used ``ControlledExecutionAdapter`` (a TEST double that
only emits synthetic "completed in simulation" strings). This test proves the PRODUCTION executor is
the governed, observable, durable one: each action materializes a REAL artifact (BEFORE != AFTER on the
filesystem), crosses Q4 (DRY_RUN blocks it), records the real result in the canonical execution state,
persists via the durable Work authority, and survives a restart. The test double stays OUT of the
production wiring.
"""
import os
import tempfile

import pytest

from src.eureka.universe.work_store import WorkStore
from src.eureka.universe.canonical_state import CanonicalWorkState, ExecutionStep, WorkResult
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.problem_model import CognitiveTask
from src.eureka.universe.action_model import ValidatedActionPlan, ActionStep
from src.eureka.universe.installer import EMInstaller
from src.eureka.universe.governed_execution_adapter import GovernedExecutionAdapter
from src.eureka.universe.controlled_execution_adapter import ControlledExecutionAdapter
from src.eureka.universe.effect_policy import default_boundary, ExecutionMode
from src.eureka.universe.canonical_identity import canonical_state_fingerprint


def _mk_canonical(work_id="W-EX"):
    c = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="t", user_intent="u",
                                           task_category="c", problem_statement="p"))
    c.status = "RUNNING"
    c.revision = 1
    c.execution_plan.steps.append(ExecutionStep(
        step_id="install", capability_id="install_action", target="EM Installer",
        canonical_em="EM Installer", status="RUNNING", produces_result=True))
    c.action_plan = ValidatedActionPlan(
        plan_id="AP-EXEC", prescription_ref="PRES-1",
        actions=[
            ActionStep(action_id="A1", description="materialize governed artifact", owner="ops",
                       dependencies=[], acceptance_criteria=[]),
            ActionStep(action_id="A2", description="configure output", owner="ops",
                       dependencies=["A1"], acceptance_criteria=[]),
        ],
        authority="HUMAN", provenance=["actioner"], validation_status="VALIDATED")
    return c


def _mk_task():
    return CognitiveTask(task_id="install", description="install", owner="EM Installer",
                         expected_outputs=["artifact"])


def _installer(artifact_dir, mode=ExecutionMode.REAL_EXECUTION, boundary=None):
    return EMInstaller(GovernedExecutionAdapter(boundary=boundary or default_boundary(),
                                                artifact_dir=artifact_dir, mode=mode))


def test_production_wiring_uses_real_executor_not_test_double():
    from src.eureka.universe.server import runtime
    assert isinstance(runtime.installer.adapter, GovernedExecutionAdapter)
    assert not isinstance(runtime.installer.adapter, ControlledExecutionAdapter)
    assert runtime.installer.adapter.mode == ExecutionMode.REAL_EXECUTION  # no dry-run by default


def test_real_effect_before_after():
    artifact_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-EXEC")
    # BEFORE: no execution artifact
    assert not os.listdir(artifact_dir)
    installer = _installer(artifact_dir)
    installer.execute_task(None, _mk_task(), canonical)
    # AFTER: real, observable effect (governed artifacts materialized)
    artifacts = os.listdir(artifact_dir)
    assert len(artifacts) == 2
    for f in artifacts:
        with open(os.path.join(artifact_dir, f), "r", encoding="utf-8") as fh:
            content = __import__("json").load(fh)
        assert content["artifact_kind"] == "WORK_EXECUTION_ARTIFACT"
        assert content["authority"] == "WORK_RUNTIME"
        assert content["mode"] == "REAL_EXECUTION"
        assert content["provenance"]
    # real result recorded in the canonical execution state
    es = canonical.execution_state
    assert es is not None
    assert es.result.status == "SUCCEEDED"
    assert sorted(es.result.successful_actions) == ["A1", "A2"]


def test_dry_run_blocks_real_effect():
    artifact_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-DRY")
    installer = _installer(artifact_dir, mode=ExecutionMode.DRY_RUN)
    installer.execute_task(None, _mk_task(), canonical)
    # NO artifact was written (DRY_RUN blocks the MUTATE effect)
    assert os.listdir(artifact_dir) == []
    es = canonical.execution_state
    assert es is not None
    assert es.result.status == "FAILED"   # no false success
    assert any(obs.observation_type == "GOVERNANCE_BLOCK" and obs.is_error
               for ev in es.evidence for obs in ev.observations)


def test_unauthorized_action_fails_closed():
    artifact_dir = tempfile.mkdtemp()
    adapter = GovernedExecutionAdapter(boundary=default_boundary(), artifact_dir=artifact_dir)
    from src.eureka.universe.installation_model import ExecutionAuthorization, ExecutionRequest
    plan = _mk_canonical().action_plan
    req = ExecutionRequest(request_id="REQ-1", action_plan_ref=plan.plan_id,
                           target_execution_level=1, requested_by="t")
    auth = adapter.verify_authorization(req, plan, expected_level=1)
    # authorize a SUBSET (simulate scope drift) and try to execute an unauthorized action
    auth = ExecutionAuthorization(authorization_id="AUTH-X", request_ref=req.request_id,
                                  authorized_execution_level=1, authorized_by="WorkRuntime",
                                  authorized_actions=["A1"])  # A2 not authorized
    ev = adapter.execute_action("A2", plan, auth)
    assert ev.observations[0].observation_type == "SECURITY_ERROR"
    assert ev.observations[0].is_error is True
    assert os.listdir(artifact_dir) == []   # no effect


def test_executor_failure_no_false_success():
    # point artifact_dir at an EXISTING FILE so makedirs fails -> effect fails (no false success)
    with tempfile.TemporaryDirectory() as td:
        file_path = os.path.join(td, "artifact")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("blocked path")
        canonical = _mk_canonical("W-FAIL")
        installer = _installer(file_path)   # artifact_dir is a file, not a dir
        installer.execute_task(None, _mk_task(), canonical)
        es = canonical.execution_state
        assert es.result.status in ("FAILED", "PARTIALLY_SUCCEEDED")
        assert any(obs.observation_type == "EXECUTION_ERROR" and obs.is_error
                   for ev in es.evidence for obs in ev.observations)


def test_governed_execution_mutates_canonical_after_effect():
    # Q2 fingerprint legitimately CHANGES once the canonical execution result is recorded (F1 != F2),
    # and only AFTER the governed execution (never before, never from client data).
    artifact_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-Q2")
    fp_before = canonical_state_fingerprint(canonical)
    installer = _installer(artifact_dir)
    installer.execute_task(None, _mk_task(), canonical)
    assert canonical_state_fingerprint(canonical) != fp_before   # legitimate post-execution mutation


def test_persist_and_restart_recovery():
    work_dir = tempfile.mkdtemp()
    artifact_dir = tempfile.mkdtemp()
    canonical = _mk_canonical("W-RT")
    storeA = WorkStore(work_dir)
    storeA["W-RT"] = canonical
    installer = _installer(artifact_dir)
    installer.execute_task(None, _mk_task(), canonical)
    storeA["W-RT"] = canonical   # persist the (mutated) canonical with its execution state
    # RESTART -> new WorkStore over the same storage
    storeB = WorkStore(work_dir)
    reloaded = storeB["W-RT"]
    assert reloaded.execution_state is not None
    assert reloaded.execution_state.result.status == "SUCCEEDED"
    assert sorted(reloaded.execution_state.result.successful_actions) == ["A1", "A2"]
    # the real effect survives: artifacts still on disk
    assert len(os.listdir(artifact_dir)) == 2
