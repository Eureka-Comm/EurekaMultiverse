"""EUREKA 5.1 — Read-only Observability / Audit Projection over the Scenario pipeline.

This is a PURE READ MODEL: it assembles, from the EXISTING authorities (WorkStore + ScenarioRepository),
a single READ-ONLY projection of everything that happened for a Work/Scenario. It is:

- READ-ONLY / DERIVED / NON-CANONICAL / NON-AUTHORITATIVE (it is a view, not a new authority).
- COMPOSITION ONLY: it never writes, never mutates canonical state, never computes a new prediction /
  prescription, never authorizes / executes / promotes, and never fabricates an event or timestamp.
- NOT a store: no audit_db/observability_store — every stage is read from the durable authorities.

Every stage is tagged ``RECORDED`` (durably present in an authority), ``DERIVED`` (read as state), or
``NOT_RECORDED`` (honest absence — never invented). The Work stage links to a Scenario ONLY through
Q2 (``canonical_state_fingerprint`` == ``scenario.source_state_identity``); the Work itself is read
from the single durable Work authority.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .canonical_identity import canonical_state_fingerprint
from .projected_artifact import ArtifactScope, AuthorityClass, CanonicalStatus
from .scenario_foundation import Scenario
from .scenario_runtime import ScenarioRuntimeResult
from .scenario_decision import ScenarioDecision
from .scenario_execution import ScenarioExecution


class AuditStage(BaseModel):
    stage: str                                   # WORK / SCENARIO / WHAT_IF / COMPARE / DECISION / EXECUTION
    status: str                                  # RECORDED / DERIVED / NOT_RECORDED
    entity_id: str = ""
    authority: str = AuthorityClass.PROJECTED.value
    canonical_status: str = CanonicalStatus.NON_CANONICAL.value
    scope: str = ArtifactScope.SCENARIO.value
    timestamp: Optional[str] = None              # only a REAL persisted timestamp; never invented
    provenance: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditProjection(BaseModel):
    scenario_id: str
    source_state_identity: str
    work: Optional[Dict[str, Any]] = None         # linked Work view (via Q2), if resolved
    stages: List[AuditStage] = Field(default_factory=list)
    projected_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    decision: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    provenance: List[str] = Field(default_factory=list)


def build_audit(repository, work_resolver, scenario_id: str, work_id: Optional[str] = None) -> AuditProjection:
    """Assemble the read-only audit projection for a Scenario (fail-closed on missing scenario)."""
    scenario: Optional[Scenario] = repository.get_scenario(scenario_id)
    if scenario is None:
        raise ValueError(f"SCENARIO_NOT_FOUND:{scenario_id}")

    result: Optional[ScenarioRuntimeResult] = repository.get_result(scenario_id)
    decision: Optional[ScenarioDecision] = repository.get_decision(scenario_id)
    execution: Optional[ScenarioExecution] = repository.get_execution(scenario_id)

    # ---- WORK stage (link via Q2 identity; optional) ------------------------- #
    work_view: Optional[Dict[str, Any]] = None
    work_stage = AuditStage(stage="WORK", status="NOT_RECORDED", authority=AuthorityClass.PROJECTED.value)
    if work_id:
        work = work_resolver(work_id) if work_resolver else None
        if work is not None:
            linked = canonical_state_fingerprint(work) == scenario.source_state_identity
            work_view = {
                "work_id": work_id,
                "source_state_identity": canonical_state_fingerprint(work),
                "revision": getattr(work, "revision", None),
                "status": getattr(work, "status", None),
                "linked_to_scenario": linked,
                "provenance": ["work-authority", f"work_id:{work_id}"],
            }
            work_stage = AuditStage(
                stage="WORK",
                status="RECORDED" if linked else "DERIVED",
                entity_id=work_id,
                authority=AuthorityClass.PROJECTED.value,
                canonical_status=CanonicalStatus.NON_CANONICAL.value,
                details={"linked_to_scenario": linked, "revision": getattr(work, "revision", None)},
                provenance=["work-authority", f"work_id:{work_id}"],
            )

    # ---- stages ------------------------------------------------------------- #
    stages: List[AuditStage] = [
        work_stage,
        AuditStage(stage="SCENARIO", status="RECORDED", entity_id=scenario.scenario_id,
                   provenance=list(scenario.provenance), details={"assumptions": list(scenario.assumptions)}),
        AuditStage(
            stage="WHAT_IF", status="RECORDED" if result is not None else "NOT_RECORDED",
            entity_id=scenario.scenario_id,
            provenance=list(result.provenance) if result else [],
            details={"artifact_count": len(result.projected_artifacts) if result else 0},
        ),
        AuditStage(stage="COMPARE", status="NOT_RECORDED"),  # comparison is computed on demand, not stored
        AuditStage(
            stage="DECISION", status="RECORDED" if decision is not None else "NOT_RECORDED",
            entity_id=decision.decision_id if decision else "",
            authority=decision.authority.value if decision else AuthorityClass.PROJECTED.value,
            timestamp=decision.created_at if decision else None,
            provenance=list(decision.provenance) if decision else [],
        ),
        AuditStage(
            stage="EXECUTION", status="RECORDED" if execution is not None else "NOT_RECORDED",
            entity_id=execution.execution_id if execution else "",
            authority=execution.authority.value if execution else AuthorityClass.PROJECTED.value,
            provenance=list(execution.provenance) if execution else [],
            details={"action_id": execution.action_id, "status": execution.status.value} if execution else {},
        ),
    ]

    projected = [a.model_dump(mode="json") for a in result.projected_artifacts] if result else []
    provenance = list(scenario.provenance)
    if result:
        provenance += list(result.provenance)
    if decision:
        provenance += list(decision.provenance)
    if execution:
        provenance += list(execution.provenance)

    return AuditProjection(
        scenario_id=scenario.scenario_id,
        source_state_identity=scenario.source_state_identity,
        work=work_view,
        stages=stages,
        projected_artifacts=projected,
        decision=decision.model_dump(mode="json") if decision else None,
        execution=execution.model_dump(mode="json") if execution else None,
        provenance=provenance,
    )
