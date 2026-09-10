"""EUREKA 5.1 — Governed REAL execution adapter for the CANONICAL work runtime (PRODUCTION).

This is the production replacement for ``ControlledExecutionAdapter`` (which remains a TEST double).
The two adapters share the same surface (``verify_authorization`` / ``execute_action``) so the Installer
contract is unchanged; only the production wiring differs.

REAL effect: each executed action materializes a governed, durable, provenance-bearing artifact
(a real file under ``data/work-executions``). The artifact content is derived from the REAL action +
plan + request + authorization — never a hardcoded "completed" string, never a returned dict alone.

Governance:
- The write crosses Q4 (``EffectBoundary``/``guarded_dump_json``, capability ``work.execution``, MUTATE).
- ``DRY_RUN`` blocks the write (no artifact, an error observation is emitted) → no real effect.
- ``REAL_EXECUTION`` (with a runtime authorization) allows the write → real, observable effect.
- Authorization is SERVER-SIDE: it is derived from the validated action plan, never from the client
  (the client cannot claim authority / execution_mode / success / bypass_governance).
- Failure of the write (PolicyError / IO error) produces an error observation → the Installer marks the
  action failed; the system never reports false success.
"""
from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import List, Optional

from .installation_model import (ExecutionRequest, ExecutionAuthorization, ExecutionObservation,
                                 ExecutionEvidence)
from .action_model import ValidatedActionPlan
from .effect_policy import (EffectBoundary, DryRunContext, ExecutionMode, PolicyError,
                            default_boundary, guarded_dump_json, EffectClass)


class GovernedExecutionAdapter:
    """Production execution adapter: a governed, observable, durable action effect.

    ``mode`` selects the Q4 execution mode for the effect (REAL_EXECUTION by default; the runtime flips
    it to DRY_RUN for a dry-run context, which blocks the write — no effect).
    """

    def __init__(self, boundary: Optional[EffectBoundary] = None,
                 artifact_dir: str = "data/work-executions",
                 mode: ExecutionMode = ExecutionMode.REAL_EXECUTION) -> None:
        self._boundary = boundary or default_boundary()
        self.artifact_dir = artifact_dir
        self.mode = mode
        self.history: List[ExecutionObservation] = []

    # ---- SERVER-SIDE authority resolution (never from the client) ----------- #
    def verify_authorization(self, request: ExecutionRequest, plan: ValidatedActionPlan,
                             expected_level: int = 1) -> ExecutionAuthorization:
        """Derive the execution authorization SERVER-SIDE: the runtime authorizes exactly the actions
        present in the VALIDATED action plan (never a client-supplied action set / authority)."""
        level = expected_level
        return ExecutionAuthorization(
            authorization_id=f"AUTH-{uuid.uuid4().hex[:6]}",
            request_ref=request.request_id,
            authorized_execution_level=level,
            authorized_by="WorkRuntime",   # server-side authority; not a client claim
            authorized_actions=[a.action_id for a in plan.actions],
        )

    # ---- governed, observable, durable REAL effect -------------------------- #
    def execute_action(self, action_id: str, plan: ValidatedActionPlan,
                       auth: ExecutionAuthorization) -> ExecutionEvidence:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. authorize (fail-closed on an action the runtime did not authorize).
        if action_id not in auth.authorized_actions:
            return ExecutionEvidence(evidence_id=f"EV-{uuid.uuid4().hex[:6]}", action_id=action_id,
                                     observations=[ExecutionObservation(
                                         action_id=action_id, timestamp=now,
                                         observation_type="SECURITY_ERROR",
                                         content="Action not authorized", is_error=True)])

        # 2. Q4 classification + policy gate FIRST (never write before the gate).
        ctx = DryRunContext(capability_id="work.execution", target=f"fs:work-execution:{action_id}",
                            mode=self.mode, authorization=f"WORK_RUNTIME:{plan.plan_id}",
                            execution_level=1, required_execution_level=1)
        try:
            self._boundary.enforce(ctx)
        except PolicyError as e:
            # DRY_RUN / unauthorized / unknown effect -> BLOCK, NO artifact (no real effect).
            return ExecutionEvidence(evidence_id=f"EV-{uuid.uuid4().hex[:6]}", action_id=action_id,
                                     observations=[ExecutionObservation(
                                         action_id=action_id, timestamp=now,
                                         observation_type="GOVERNANCE_BLOCK",
                                         content=f"{e.reason_code}: {e.message}", is_error=True)])

        # 3. locate the real action and materialize a governed artifact (the observable effect).
        action = next((a for a in plan.actions if a.action_id == action_id), None)
        artifact_content = {
            "artifact_kind": "WORK_EXECUTION_ARTIFACT",
            "action_id": action_id,
            "action_description": getattr(action, "description", "") if action else "",
            "action_owner": getattr(action, "owner", "") if action else "",
            "plan_id": plan.plan_id,
            "prescription_ref": plan.prescription_ref,
            "authorization_id": auth.authorization_id,
            "authorized_by": auth.authorized_by,
            "mode": self.mode.value,
            "authority": "WORK_RUNTIME",
            "timestamp": now,
            "provenance": [f"plan:{plan.plan_id}", f"action:{action_id}", f"auth:{auth.authorization_id}"],
        }
        artifact_id = f"EXEC-ART-{uuid.uuid4().hex[:8].upper()}"
        path = os.path.join(self.artifact_dir, f"{plan.plan_id}-{action_id}-{artifact_id}.json")
        try:
            os.makedirs(self.artifact_dir, exist_ok=True)
            guarded_dump_json(self._boundary, path, artifact_content,
                              mode=self.mode, authorization=f"WORK_RUNTIME:{plan.plan_id}",
                              capability_id="work.execution", target="fs")
        except (PolicyError, OSError) as e:
            # effect failed -> error observation, no false success
            reason = getattr(e, "reason_code", "EXECUTION_ERROR")
            return ExecutionEvidence(evidence_id=f"EV-{uuid.uuid4().hex[:6]}", action_id=action_id,
                                     observations=[ExecutionObservation(
                                         action_id=action_id, timestamp=now,
                                         observation_type="EXECUTION_ERROR",
                                         content=f"{reason}: real effect failed ({e})", is_error=True)])

        # 4. REAL observable observation referencing the actual artifact.
        bytes_written = os.path.getsize(path) if os.path.exists(path) else 0
        observation = ExecutionObservation(
            action_id=action_id, timestamp=now, observation_type="ARTIFACT",
            content=f"governed artifact materialized: {path} ({bytes_written} bytes)",
            is_error=False)
        self.history.append(observation)
        return ExecutionEvidence(evidence_id=f"EV-{uuid.uuid4().hex[:6]}", action_id=action_id,
                                 observations=[observation])
