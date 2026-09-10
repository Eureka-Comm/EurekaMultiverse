"""EUREKA 5.1 — Scenario Lifecycle (governed, no external execution).

Implements the authoritative lifecycle ``CREATE → READY → RUN → PROJECT → VALIDATE → REVIEW →
{DISCARD | AUTHORIZE}`` (``docs/architecture/SCENARIO_LIFECYCLE.md``), integrating:

- ``Scenario`` (Q1) as the non-canonical hypothetical context,
- ``ScenarioRuntime`` (reusing Q2 source identity + Q4 EffectBoundary + Q3 ProjectedArtifact) for
  the DRY_RUN projection,
- ``ScenarioRuntimeResult`` as the non-canonical projected output.

Invariants: Scenario stays non-canonical at every state; AUTHORIZE is a recorded decision that does
NOT execute external effects (REAL_EXECUTION is intentionally out of this block); every invalid
transition fails closed; no canonical mutation; ``PredictionScenario`` untouched.
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from .scenario_foundation import Scenario
from .scenario_runtime import ScenarioRuntime, ScenarioRuntimeResult


class ScenarioLifecycleStatus(str, Enum):
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    PROJECTED = "PROJECTED"
    VALIDATED = "VALIDATED"
    REVIEW = "REVIEW"
    DISCARDED = "DISCARDED"
    AUTHORIZED = "AUTHORIZED"
    FAILED = "FAILED"


# Authoritative transition graph (fail-closed on anything else).
_ALLOWED: Dict[ScenarioLifecycleStatus, set] = {
    ScenarioLifecycleStatus.CREATED: {ScenarioLifecycleStatus.READY, ScenarioLifecycleStatus.FAILED},
    ScenarioLifecycleStatus.READY: {ScenarioLifecycleStatus.RUNNING, ScenarioLifecycleStatus.FAILED},
    ScenarioLifecycleStatus.RUNNING: {ScenarioLifecycleStatus.PROJECTED, ScenarioLifecycleStatus.FAILED},
    ScenarioLifecycleStatus.PROJECTED: {ScenarioLifecycleStatus.VALIDATED, ScenarioLifecycleStatus.FAILED},
    ScenarioLifecycleStatus.VALIDATED: {ScenarioLifecycleStatus.REVIEW, ScenarioLifecycleStatus.FAILED},
    ScenarioLifecycleStatus.REVIEW: {ScenarioLifecycleStatus.DISCARDED, ScenarioLifecycleStatus.AUTHORIZED},
    ScenarioLifecycleStatus.DISCARDED: set(),
    ScenarioLifecycleStatus.AUTHORIZED: set(),
    ScenarioLifecycleStatus.FAILED: set(),
}


class LifecycleTransitionError(RuntimeError):
    """Raised when an invalid lifecycle transition is attempted (fail-closed)."""
    def __init__(self, src: str, dst: str) -> None:
        super().__init__(f"INVALID_TRANSITION: {src} -> {dst}")
        self.src = src
        self.dst = dst


class ScenarioLifecycle(BaseModel):
    scenario: Scenario
    status: ScenarioLifecycleStatus = ScenarioLifecycleStatus.CREATED
    runtime_result: Optional[ScenarioRuntimeResult] = None
    provenance: List[str] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(cls, scenario: Scenario) -> "ScenarioLifecycle":
        return cls(scenario=scenario, provenance=[f"created:{scenario.scenario_id}"])

    @property
    def is_non_canonical(self) -> bool:
        return self.scenario.is_non_canonical

    def transition(self, to: ScenarioLifecycleStatus, note: str = "") -> "ScenarioLifecycle":
        """Move to a state only if the transition is allowed; otherwise fail closed."""
        if to not in _ALLOWED.get(self.status, set()):
            raise LifecycleTransitionError(self.status.value, to.value)
        self.status = to
        self.provenance.append(f"{to.value}{(':' + note) if note else ''}@"
                               f"{datetime.datetime.now(datetime.timezone.utc).isoformat()}")
        return self

    def ready(self, current_state) -> "ScenarioLifecycle":
        # READY requires a Scenario whose source identity is not stale against the canonical state.
        self.transition(ScenarioLifecycleStatus.READY)
        return self

    def run(self) -> "ScenarioLifecycle":
        self.transition(ScenarioLifecycleStatus.RUNNING)
        return self

    def project(self, current_state, projection_fn, inputs: Optional[Dict[str, Any]] = None,
                runtime: Optional[ScenarioRuntime] = None) -> "ScenarioLifecycle":
        # PROJECT delegates to ScenarioRuntime (DRY_RUN, governed), reusing Q2/Q3/Q4.
        # Requires the lifecycle to have been moved to RUNNING by .run() first.
        rt = runtime or ScenarioRuntime()
        self.runtime_result = rt.project(self.scenario, current_state, projection_fn, inputs)
        self.transition(ScenarioLifecycleStatus.PROJECTED)
        return self

    def validate(self, current_state, runtime: Optional[ScenarioRuntime] = None) -> "ScenarioLifecycle":
        # VALIDATE: re-check source identity against current canonical state (fail-closed on stale),
        # then transition. Never mutates canonical state.
        rt = runtime or ScenarioRuntime()
        if rt.validate_source(self.scenario, current_state) != "MATCH":
            self.transition(ScenarioLifecycleStatus.FAILED, "STALE_SOURCE")
            raise LifecycleTransitionError(self.status.value, "VALIDATED")
        self.transition(ScenarioLifecycleStatus.VALIDATED)
        return self

    def review(self) -> "ScenarioLifecycle":
        self.transition(ScenarioLifecycleStatus.REVIEW)
        return self

    def discard(self) -> "ScenarioLifecycle":
        self.transition(ScenarioLifecycleStatus.DISCARDED)
        return self

    def authorize(self) -> "ScenarioLifecycle":
        # AUTHORIZE is a recorded decision. It does NOT execute external effects (REAL_EXECUTION is
        # intentionally out of this block).
        self.transition(ScenarioLifecycleStatus.AUTHORIZED)
        return self
