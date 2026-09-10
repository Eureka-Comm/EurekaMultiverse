"""EUREKA 5.1 — Projected Artifact Authority (Q3).

A formal, non-canonical artifact type that can NEVER be mistaken implicitly for a canonical
PREDICTION / RECOMMENDATION / RESULT / CANONICAL STATE. The infrastructure enforces:

- ``scope`` must be SCENARIO (non-canonical); CANONICAL scope is rejected.
- ``authority`` must be ``PROJECTED``; canonical/result/recommendation/human-decision authority is
  rejected at construction (no implicit promotion).
- ``canonical_status`` must be NON_CANONICAL.
- a ``source_state_identity`` (reused from Q2 ``canonical_state_fingerprint``) is required.
- provenance is required.

There is deliberately NO promotion workflow here — only the structural boundary that makes a
hypothetical artifact non-canonical and keeps the identity of the canonical source it was "built
on" (Q2). Creating these artifacts does NOT mutate canonical state.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from .canonical_identity import canonical_state_fingerprint, compare_source_identity


class ArtifactScope(str, Enum):
    CANONICAL = "CANONICAL"
    SCENARIO = "SCENARIO"


class CanonicalStatus(str, Enum):
    CANONICAL = "CANONICAL"
    NON_CANONICAL = "NON_CANONICAL"


class AuthorityClass(str, Enum):
    """Authority of an artifact. Projected artifacts carry only PROJECTED."""
    PROJECTED = "PROJECTED"            # hypothetical / non-canonical
    CANONICAL = "CANONICAL"            # canonical runtime authority
    RESULT = "RESULT"                  # published result authority
    RECOMMENDATION = "RECOMMENDATION"  # system recommendation authority
    HUMAN_DECISION = "HUMAN_DECISION"  # human decision authority


# Authorities that a ProjectedArtifact must NEVER carry (no implicit narrowing to authoritative).
AUTHORITATIVE = frozenset({
    AuthorityClass.CANONICAL, AuthorityClass.RESULT,
    AuthorityClass.RECOMMENDATION, AuthorityClass.HUMAN_DECISION,
})


class ProjectedArtifact(BaseModel):
    artifact_id: str
    artifact_kind: str                       # e.g. "FINDING", "PREDICTION", "RESULT"
    scope: ArtifactScope = ArtifactScope.SCENARIO
    authority: AuthorityClass = AuthorityClass.PROJECTED
    provenance: List[str] = Field(default_factory=list)
    source_state_identity: str               # Q2 canonical_state_fingerprint of the source state
    canonical_status: CanonicalStatus = CanonicalStatus.NON_CANONICAL
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("scope")
    @classmethod
    def _reject_canonical_scope(cls, v: ArtifactScope) -> ArtifactScope:
        if v == ArtifactScope.CANONICAL:
            raise ValueError("projected artifact scope must be SCENARIO (non-canonical)")
        return v

    @field_validator("authority")
    @classmethod
    def _reject_authoritative_authority(cls, v: AuthorityClass) -> AuthorityClass:
        if v in AUTHORITATIVE:
            raise ValueError(f"projected artifact cannot carry authoritative authority: {v.value}")
        return v

    @field_validator("canonical_status")
    @classmethod
    def _reject_canonical_status(cls, v: CanonicalStatus) -> CanonicalStatus:
        if v == CanonicalStatus.CANONICAL:
            raise ValueError("projected artifact canonical_status must be NON_CANONICAL")
        return v

    @model_validator(mode="after")
    def _require_identity_and_provenance(self) -> "ProjectedArtifact":
        if not self.source_state_identity:
            raise ValueError("projected artifact requires source_state_identity")
        if not self.provenance:
            raise ValueError("projected artifact requires provenance")
        return self

    @property
    def is_non_canonical(self) -> bool:
        return (self.scope == ArtifactScope.SCENARIO
                and self.authority == AuthorityClass.PROJECTED
                and self.canonical_status == CanonicalStatus.NON_CANONICAL)

    @classmethod
    def from_source(cls, artifact_id: str, artifact_kind: str, source_state, provenance: Optional[List[str]] = None) -> "ProjectedArtifact":
        """Build a projected artifact bound to a canonical source state (reuses Q2 identity)."""
        identity = canonical_state_fingerprint(source_state)
        return cls(
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            source_state_identity=identity,
            provenance=provenance or [f"source:{identity}"],
        )

    def verify_source(self, current_state) -> str:
        """Return MATCH/STALE against the current canonical state (Q2 stale detection)."""
        return compare_source_identity(self.source_state_identity, current_state)
