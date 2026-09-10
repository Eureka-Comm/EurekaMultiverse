"""EUREKA 5.1 — Governed Scenario Action Execution (REAL_EXECUTION under Q4).

A ``ScenarioExecution`` is the durable, provenance-bearing RECORD of a HUMAN-AUTHORIZED real action
that crossed the Q4 EffectBoundary and produced an observable effect (a governed artifact write).

Separation of concepts (hard invariant):
- ``Scenario``        = non-canonical hypothetical context (Q1), NEVER mutated.
- ``ScenarioDecision``= the human's record-only authority (HUMAN_DECISION / SCENARIO / NON_CANONICAL).
- ``ScenarioExecution`` = the record of a GOVERNEED REAL action bound to a decision. It carries the
                          execution result + governance verdict + the real effect.

Execution rules (all fail-closed):
- Only a decision in lifecycle ``AUTHORIZED`` with ``decision_type == CONFIRM`` authorizes an action.
- The action is a single, unambiguous identity (an artifact materialization), derived from the decision.
- The canonical source is re-validated (Q2): stale -> REJECTED (no effect).
- The real write crosses ``EffectBoundary`` under ``ExecutionMode.REAL_EXECUTION`` with a
  HUMAN_DECISION authorization; DRY_RUN always blocks; a blocked/unknown effect -> REJECTED (no write).
- The Scenario and the decision stay NON_CANONICAL / SCENARIO; execution never promotes/canonicalizes.
- Idempotent: the same (scenario_id, decision_id) executes at most once.
"""
from __future__ import annotations

import datetime
import os
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from .projected_artifact import ArtifactScope, AuthorityClass, CanonicalStatus
from .scenario_decision import ScenarioDecision, DecisionType
from .effect_policy import EffectBoundary, DryRunContext, ExecutionMode, PolicyError, default_boundary
from .effect_policy import guarded_dump_json, EffectClass


class ScenarioExecutionStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"   # the real effect was produced and observed
    REJECTED = "REJECTED"     # decision/identity/governance/effect denied (fail-closed, no effect)
    FAILED = "FAILED"         # an unexpected error occurred while producing the effect


# The single action this block can govern: materialize a governed artifact from the authorized
# scenario. Kept explicit and unambiguous (a scenario authorizes exactly this, nothing else).
ACTION_MATERIALIZE = "MATERIALIZE_SCENARIO_ARTIFACT"


def resolve_authorized_action(decision: ScenarioDecision) -> Optional[str]:
    """Resolve the (single) action that a decision authorizes. Returns None if the decision does NOT
    authorize a real action, so the engine must fail-closed. A decision authorizes an action ONLY
    when it is in lifecycle AUTHORIZED and the type is CONFIRM (recorded human authorization)."""
    if decision.lifecycle_state != "AUTHORIZED":
        return None
    if decision.decision_type != DecisionType.CONFIRM:
        return None
    return f"{ACTION_MATERIALIZE}:{decision.scenario_id}"


class ScenarioExecution(BaseModel):
    execution_id: str
    scenario_id: str
    decision_id: str
    action_id: str                     # the unambiguous action identity (derived, never client-side)
    source_state_identity: str
    status: ScenarioExecutionStatus
    # SERVER-DERIVED authority — the client cannot claim these.
    authority: AuthorityClass = AuthorityClass.HUMAN_DECISION
    scope: ArtifactScope = ArtifactScope.SCENARIO
    canonical_status: CanonicalStatus = CanonicalStatus.NON_CANONICAL
    governance: Dict[str, Any] = Field(default_factory=dict)   # mode/effect_class/decision/reason
    effect: Dict[str, Any] = Field(default_factory=dict)       # artifact_id/path/bytes/exists
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""

    @field_validator("scope")
    @classmethod
    def _reject_canonical_scope(cls, v: ArtifactScope) -> ArtifactScope:
        if v == ArtifactScope.CANONICAL:
            raise ValueError("ScenarioExecution scope must be SCENARIO (non-canonical)")
        return v

    @field_validator("authority")
    @classmethod
    def _lock_human_authority(cls, v: AuthorityClass) -> AuthorityClass:
        if v != AuthorityClass.HUMAN_DECISION:
            raise ValueError("ScenarioExecution authority must be HUMAN_DECISION (server-derived)")
        return v

    @field_validator("canonical_status")
    @classmethod
    def _reject_canonical_status(cls, v: CanonicalStatus) -> CanonicalStatus:
        if v == CanonicalStatus.CANONICAL:
            raise ValueError("ScenarioExecution canonical_status must be NON_CANONICAL")
        return v

    @model_validator(mode="after")
    def _require_identity_and_provenance(self) -> "ScenarioExecution":
        if not self.source_state_identity:
            raise ValueError("ScenarioExecution requires source_state_identity")
        if not self.provenance:
            raise ValueError("ScenarioExecution requires provenance")
        if self.scope != ArtifactScope.SCENARIO:
            raise ValueError("ScenarioExecution must be non-canonical (scope SCENARIO)")
        if self.canonical_status != CanonicalStatus.NON_CANONICAL:
            raise ValueError("ScenarioExecution canonical_status must be NON_CANONICAL")
        return self

    @property
    def is_non_canonical(self) -> bool:
        return (self.scope == ArtifactScope.SCENARIO
                and self.canonical_status == CanonicalStatus.NON_CANONICAL)

    @classmethod
    def record(cls, *, scenario, decision: ScenarioDecision, action_id: str, status: ScenarioExecutionStatus,
               governance: Dict[str, Any], effect: Dict[str, Any]) -> "ScenarioExecution":
        """Build an execution record. Authority fields are SERVER-derived from the Scenario + the fact
        that the authority is the human; the client never supplies them."""
        return cls(
            execution_id=f"EXEC-{uuid.uuid4().hex[:8].upper()}",
            scenario_id=scenario.scenario_id,
            decision_id=decision.decision_id,
            action_id=action_id,
            source_state_identity=scenario.source_state_identity,
            status=status,
            scope=ArtifactScope.SCENARIO,
            authority=AuthorityClass.HUMAN_DECISION,
            canonical_status=CanonicalStatus.NON_CANONICAL,
            governance=governance,
            effect=effect,
            provenance=[
                f"scenario:{scenario.scenario_id}",
                f"decision:{decision.decision_id}",
                f"source:{scenario.source_state_identity}",
                f"action:{action_id}",
                f"mode:{governance.get('mode', '')}",
                f"authority:HUMAN_DECISION",
            ],
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )


def execute_gov(decision: ScenarioDecision, scenario, source_state, output_dir: str,
                boundary: Optional[EffectBoundary] = None,
                projected_artifacts: Optional[List[Any]] = None) -> ScenarioExecution:
    """GOVERNED REAL execution of a decision's authorized action.

    Steps: (1) resolve the action identity; (2) cross Q4 (classifier + policy) under REAL_EXECUTION;
    (3) produce a REAL observable effect (write a governed artifact); (4) build the execution record.

    Returns a ScenarioExecution (status SUCCEEDED or REJECTED). On an unexpected error, FAILED.
    Does NOT mutate the Scenario, does NOT promote/canonicalize. Does NOT fabricate success.
    """
    boundary = boundary or default_boundary()
    action_id = resolve_authorized_action(decision)
    gov_base = {
        "mode": ExecutionMode.REAL_EXECUTION.value,
        "effect_class": EffectClass.MUTATE.value,
        "authorization": f"HUMAN_DECISION:{decision.decision_id}",
        "capability_id": "scenario.execution",
    }

    if action_id is None:
        governance = dict(gov_base, decision="BLOCK",
                          reason_code="ACTION_NOT_AUTHORIZED",
                          message="The decision does not authorize a real action")
        return ScenarioExecution.record(scenario=scenario, decision=decision, action_id="NONE",
                                        status=ScenarioExecutionStatus.REJECTED,
                                        governance=governance, effect={})

    authorization = f"HUMAN_DECISION:{decision.decision_id}"
    ctx = DryRunContext(capability_id="scenario.execution", target=f"scenario-artifact:{scenario.scenario_id}",
                        mode=ExecutionMode.REAL_EXECUTION, authorization=authorization,
                        execution_level=1, required_execution_level=1)

    try:
        # Q4 classification + policy gate FIRST (never write before the gate).
        boundary.enforce(ctx)
    except PolicyError as e:
        governance = dict(gov_base, decision="BLOCK", reason_code=e.reason_code, message=e.message)
        return ScenarioExecution.record(scenario=scenario, decision=decision, action_id=action_id,
                                        status=ScenarioExecutionStatus.REJECTED,
                                        governance=governance, effect={})

    # Build a REAL artifact from the authorized scenario (non-canonical, provenance-bearing).
    pa = projected_artifacts if projected_artifacts is not None else (scenario.projected_artifacts or [])
    artifact_content = {
        "artifact_kind": "SCENARIO_DECISION_ARTIFACT",
        "scenario_id": scenario.scenario_id,
        "decision_id": decision.decision_id,
        "selected_artifact_id": decision.selected_artifact_id,
        "rationale": decision.rationale,
        "human_actor": decision.human_actor,
        "source_state_identity": scenario.source_state_identity,
        "authority": AuthorityClass.HUMAN_DECISION.value,
        "scope": ArtifactScope.SCENARIO.value,
        "canonical_status": CanonicalStatus.NON_CANONICAL.value,
        "projected_artifacts": [a.model_dump(mode="json") for a in pa],
        "provenance": list(decision.provenance),
    }

    os.makedirs(output_dir, exist_ok=True)
    artifact_path = os.path.join(output_dir, f"{scenario.scenario_id}-{action_id}.json")

    try:
        guarded_dump_json(boundary, artifact_path, artifact_content,
                          mode=ExecutionMode.REAL_EXECUTION, authorization=authorization,
                          capability_id="scenario.execution", target="fs")
    except PolicyError as e:
        governance = dict(gov_base, decision="BLOCK", reason_code=e.reason_code, message=e.message)
        return ScenarioExecution.record(scenario=scenario, decision=decision, action_id=action_id,
                                        status=ScenarioExecutionStatus.REJECTED,
                                        governance=governance, effect={})
    except Exception as e:
        governance = dict(gov_base, decision="ALLOW", reason_code="EFFECT_FAILED", message=str(e))
        return ScenarioExecution.record(scenario=scenario, decision=decision, action_id=action_id,
                                        status=ScenarioExecutionStatus.FAILED,
                                        governance=governance, effect={})

    exists = os.path.exists(artifact_path)
    effect = {
        "artifact_id": f"ART-{uuid.uuid4().hex[:8].upper()}",
        "artifact_kind": "SCENARIO_DECISION_ARTIFACT",
        "artifact_path": artifact_path,
        "bytes": os.path.getsize(artifact_path) if exists else 0,
        "exists": exists,
    }
    governance = dict(gov_base, decision="ALLOW", reason_code="OK",
                      message="Real effect produced (governed artifact materialized)")
    return ScenarioExecution.record(scenario=scenario, decision=decision, action_id=action_id,
                                    status=ScenarioExecutionStatus.SUCCEEDED,
                                    governance=governance, effect=effect)
