"""EUREKA 5.1 — Scenario Foundation Separation (Q1).

A transversal, NON-CANONICAL hypothetical-context foundation, deliberately distinct from:

- ``PredictionScenario`` (Predictor-specific predictive structure, kept untouched).
- ``CanonicalWorkState`` (the single source of truth — Scenario is never that).

Scenario represents a governed hypothetical context: identity, source-state identity (Q2)
assumptions, provenance, projected artifacts (Q3) and governance metadata. It is inherently
non-canonical (``scope`` must be SCENARIO, ``status`` only HYPOTHETICAL) and has NO execution
API (no run/execute/simulate/promote/schedule). Creating/validating it never mutates canonical state.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from .canonical_identity import canonical_state_fingerprint, compare_source_identity
from .projected_artifact import ArtifactScope, ProjectedArtifact


class ScenarioStatus(str, Enum):
    """Only non-canonical states exist; there is no CANONICAL value by design."""
    HYPOTHETICAL = "HYPOTHETICAL"


class Scenario(BaseModel):
    scenario_id: str
    source_state_identity: str                 # from Q2 canonical_state_fingerprint
    scope: ArtifactScope = ArtifactScope.SCENARIO   # non-canonical scope (reuse Q3 enum)
    status: ScenarioStatus = ScenarioStatus.HYPOTHETICAL
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    projected_artifacts: List[ProjectedArtifact] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("scope")
    @classmethod
    def _reject_canonical_scope(cls, v: ArtifactScope) -> ArtifactScope:
        if v == ArtifactScope.CANONICAL:
            raise ValueError("Scenario scope must be SCENARIO (non-canonical)")
        return v

    @model_validator(mode="after")
    def _require_identity_and_provenance(self) -> "Scenario":
        if not self.source_state_identity:
            raise ValueError("Scenario requires source_state_identity")
        if not self.provenance:
            raise ValueError("Scenario requires provenance")
        if self.scope != ArtifactScope.SCENARIO:
            raise ValueError("Scenario must be non-canonical (scope SCENARIO)")
        return self

    @property
    def is_non_canonical(self) -> bool:
        return self.scope == ArtifactScope.SCENARIO and self.status == ScenarioStatus.HYPOTHETICAL

    @classmethod
    def from_source(cls, scenario_id: str, source_state, assumptions=None,
                    projected_artifacts=None, provenance: Optional[List[str]] = None) -> "Scenario":
        """Foundation factory bound to a canonical source state (reuses Q2 identity)."""
        identity = canonical_state_fingerprint(source_state)
        return cls(
            scenario_id=scenario_id,
            source_state_identity=identity,
            assumptions=assumptions or [],
            projected_artifacts=projected_artifacts or [],
            provenance=provenance or [f"source:{identity}"],
        )

    def verify_source(self, current_state) -> str:
        """Return MATCH/STALE against the current canonical state (Q2)."""
        return compare_source_identity(self.source_state_identity, current_state)

    # NOTE: there is intentionally NO run/execute/simulate/promote/schedule method here.
