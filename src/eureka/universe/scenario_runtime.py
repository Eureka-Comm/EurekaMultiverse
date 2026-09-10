"""EUREKA 5.1 — Scenario Runtime (first functional Runtime block toward WHAT-IF).

A governed, hypothetical computation runtime that operates ONLY on a ``Scenario`` (Q1) and
produces non-canonical ``ProjectedArtifact`` outputs (Q3), reusing:

- Q2 ``compare_source_identity`` for fail-closed STALE-source validation,
- Q4 ``EffectBoundary``/``ExecutionPolicy`` (DRY_RUN) so a hypothetical computation can never
  mutate canonical state or execute a real side effect,
- Q3 ``ProjectedArtifact`` for the outputs, which are non-canonical by construction.

It never mutates ``CanonicalWorkState`` and never runs WHAT-IF end-to-end; it only demonstrates
the governed hypothetical pipeline (Scenario -> validate -> project -> governed non-canonical result).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from .canonical_identity import compare_source_identity
from .effect_policy import EffectBoundary, EffectClass, ExecutionMode, DryRunContext, default_boundary
from .projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass, CanonicalStatus
from .scenario_foundation import Scenario, ScenarioStatus

# The governed capability used to classify the hypothetical computation as COMPUTE (non-mutating).
SCENARIO_PROJECTION_CAPABILITY = "scenario.projection"


class ScenarioRuntimeResult(BaseModel):
    """Governed, NON-CANONICAL outcome of a Scenario Runtime projection."""
    scenario_id: str
    source_state_identity: str
    scope: ArtifactScope = ArtifactScope.SCENARIO
    authority: AuthorityClass = AuthorityClass.PROJECTED
    canonical_status: CanonicalStatus = CanonicalStatus.NON_CANONICAL
    status: ScenarioStatus = ScenarioStatus.HYPOTHETICAL
    projected_artifacts: List[ProjectedArtifact] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_non_canonical(self) -> bool:
        return (self.scope == ArtifactScope.SCENARIO
                and self.authority == AuthorityClass.PROJECTED
                and self.canonical_status == CanonicalStatus.NON_CANONICAL)


class ScenarioRuntime:
    """Governed runtime: validate source (fail-closed) -> project in DRY_RUN under the effect
    boundary -> produce non-canonical projected artifacts. No canonical mutation, no real side
    effects, no WHAT-IF end-to-end execution."""

    def __init__(self, boundary: Optional[EffectBoundary] = None) -> None:
        # Reuse the existing Q4 effect boundary, and classify the hypothetical computation as COMPUTE
        # so it may run (a pure projection is allowed in DRY_RUN; a MUTATE would be blocked).
        self._boundary = boundary or default_boundary()
        self._boundary.classify(SCENARIO_PROJECTION_CAPABILITY, EffectClass.COMPUTE)

    def validate_source(self, scenario: Scenario, current_state) -> str:
        return compare_source_identity(scenario.source_state_identity, current_state)

    def project(self, scenario: Scenario, current_state, projection_fn: Callable[[Scenario, Dict[str, Any]], List[ProjectedArtifact]],
                inputs: Optional[Dict[str, Any]] = None) -> ScenarioRuntimeResult:
        """Run a hypothetical computation for a Scenario in a controlled, fail-closed dry-run.

        - STALE source identity -> BLOCK (fail-closed).
        - The projection_fn runs under an EffectBoundary DRY_RUN context (COMPUTE allowed, MUTATE
          blocked) and must return ProjectedArtifacts.
        - The canonical state is never mutated.
        """
        if compare_source_identity(scenario.source_state_identity, current_state) != "MATCH":
            raise RuntimeError("STALE_SOURCE: scenario source identity does not match current canonical state")

        ctx = DryRunContext(
            capability_id=SCENARIO_PROJECTION_CAPABILITY,
            target="PROJECTED",
            mode=ExecutionMode.DRY_RUN,
            authorization=None,
            execution_level=0,
            required_execution_level=0,
        )

        # Boundary gate FIRST; the projection (a pure COMPUTE) runs only if allowed.
        artifacts = self._boundary.execute(ctx, lambda: projection_fn(scenario, inputs or {}))

        # Validate every projected artifact stays non-canonical / non-authoritative.
        for a in artifacts:
            if not a.is_non_canonical or a.authority != AuthorityClass.PROJECTED:
                raise RuntimeError("NON_CANONICAL_VIOLATION: projected artifact lost non-canonical authority")

        return ScenarioRuntimeResult(
            scenario_id=scenario.scenario_id,
            source_state_identity=scenario.source_state_identity,
            projected_artifacts=list(artifacts),
            provenance=[f"scenario:{scenario.scenario_id}", "runtime:projection"] + list(scenario.provenance),
            governance={"mode": "DRY_RUN", "non_canonical": True},
        )
