"""EUREKA 5.1 — Scenario Decision (human authority record-only, non-canonical).

A ``ScenarioDecision`` is the durable, provenance-bearing RECORD of an explicit HUMAN decision about a
hypothetical (non-canonical) Scenario. It does NOT promote, execute, or canonicalize anything.

Boundaries (hard invariant):
- scope            = SCENARIO          (non-canonical; the scenario stays hypothetical)
- canonical_status = NON_CANONICAL     (the decision never makes the scenario canonical)
- authority        = HUMAN_DECISION    (WHO decided is the human — section 31; the decision record
                                        itself carries human-decision authority, but the underlying
                                        Scenario/projected artifacts remain PROJECTED and are NOT
                                        elevated by this record)
- record-only      : recording a decision is a read/human act over non-canonical evidence. It never
                                        triggers REAL_EXECUTION, never rewrites the Scenario's scope,
                                        never converts Scenario -> canonical.

The client is allowed to supply only the human's own inputs (rationale, actor, chosen artifact,
decision type). authority/scope/canonical_status/source_state_identity are ALL SERVER-DERIVED here
and cannot be supplied by the client.
"""
from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from .projected_artifact import ArtifactScope, AuthorityClass, CanonicalStatus


class DecisionType(str, Enum):
    CONFIRM = "CONFIRM"    # the human confirms a scenario/artifact as their (non-canonical) choice
    REJECT = "REJECT"      # the human rejects the scenario evidence
    ESCALATE = "ESCALATE"  # the human escalates for further review (still record-only)


class ScenarioDecision(BaseModel):
    decision_id: str
    scenario_id: str
    lifecycle_state: str                     # REVIEW / AUTHORIZED / DISCARDED (server-recorded)
    decision_type: DecisionType
    selected_artifact_id: Optional[str] = None   # human's chosen projected artifact (optional)
    rationale: str = ""
    human_actor: str = "human"
    # SERVER-DERIVED authority — the client cannot claim these.
    scope: ArtifactScope = ArtifactScope.SCENARIO
    authority: AuthorityClass = AuthorityClass.HUMAN_DECISION
    canonical_status: CanonicalStatus = CanonicalStatus.NON_CANONICAL
    source_state_identity: str               # Q2 identity of the scenario's source (server-derived)
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""
    status: str = "RECORDED"                 # record-only; never implies execution/promotion

    @field_validator("scope")
    @classmethod
    def _reject_canonical_scope(cls, v: ArtifactScope) -> ArtifactScope:
        if v == ArtifactScope.CANONICAL:
            raise ValueError("ScenarioDecision scope must be SCENARIO (non-canonical)")
        return v

    @field_validator("authority")
    @classmethod
    def _lock_human_authority(cls, v: AuthorityClass) -> AuthorityClass:
        # A decision record's authority is the HUMAN by construction; never anything else.
        if v != AuthorityClass.HUMAN_DECISION:
            raise ValueError("ScenarioDecision authority must be HUMAN_DECISION (server-derived)")
        return v

    @field_validator("canonical_status")
    @classmethod
    def _reject_canonical_status(cls, v: CanonicalStatus) -> CanonicalStatus:
        if v == CanonicalStatus.CANONICAL:
            raise ValueError("ScenarioDecision canonical_status must be NON_CANONICAL")
        return v

    @model_validator(mode="after")
    def _require_identity_and_provenance(self) -> "ScenarioDecision":
        if not self.source_state_identity:
            raise ValueError("ScenarioDecision requires source_state_identity")
        if not self.provenance:
            raise ValueError("ScenarioDecision requires provenance")
        if self.scope != ArtifactScope.SCENARIO:
            raise ValueError("ScenarioDecision must be non-canonical (scope SCENARIO)")
        if self.canonical_status != CanonicalStatus.NON_CANONICAL:
            raise ValueError("ScenarioDecision canonical_status must be NON_CANONICAL")
        return self

    @property
    def is_non_canonical(self) -> bool:
        return (self.scope == ArtifactScope.SCENARIO
                and self.canonical_status == CanonicalStatus.NON_CANONICAL)

    @classmethod
    def record(cls, scenario, lifecycle_state: str, decision_type: DecisionType, *,
               rationale: str = "", human_actor: str = "human",
               selected_artifact_id: Optional[str] = None) -> "ScenarioDecision":
        """Build a decision record from a (non-canonical) Scenario. All authority fields are derived
        from the Scenario + the fact that the authority is the human; the client never supplies them."""
        return cls(
            decision_id=f"DEC-{uuid.uuid4().hex[:8].upper()}",
            scenario_id=scenario.scenario_id,
            lifecycle_state=lifecycle_state,
            decision_type=decision_type,
            selected_artifact_id=selected_artifact_id,
            rationale=rationale,
            human_actor=human_actor,
            scope=ArtifactScope.SCENARIO,
            authority=AuthorityClass.HUMAN_DECISION,
            canonical_status=CanonicalStatus.NON_CANONICAL,
            source_state_identity=scenario.source_state_identity,
            provenance=[
                f"scenario:{scenario.scenario_id}",
                f"source:{scenario.source_state_identity}",
                f"lifecycle:{lifecycle_state}",
                f"decision:{decision_type.value}",
                f"authority:HUMAN_DECISION",
            ],
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
