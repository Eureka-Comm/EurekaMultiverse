"""EUREKA 5.1 — Scenario Service Surface (governed domain seam).

A thin, reusable domain-facing orchestration seam that delegates to the already-verified Scenario
domain components. It does NOT re-implement their logic, does NOT own mathematics/ACFL, does NOT
perform external execution, and is transport-agnostic (HTTP/CLI/UI come later).

Delegation:
  source identity      -> canonical_identity (Q2), via Scenario.from_source
  lifecycle transitions -> ScenarioLifecycle (Q1)
  hypothetical projection -> ScenarioRuntime.project (Q2/Q3/Q4), invoked via ScenarioLifecycle
  artifact authority   -> ProjectedArtifact (Q3)
  effect governance    -> EffectBoundary (Q4), enforced inside ScenarioRuntime
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .canonical_identity import compare_source_identity
from .scenario_foundation import Scenario
from .scenario_lifecycle import ScenarioLifecycle, ScenarioLifecycleStatus, LifecycleTransitionError
from .scenario_runtime import ScenarioRuntime, ScenarioRuntimeResult
from .scenario_decision import ScenarioDecision, DecisionType
from .scenario_execution import ScenarioExecution, ScenarioExecutionStatus, execute_gov
from .scenario_real_projection import real_whatif_projection
from .effect_policy import default_boundary
from .acfl_engine import gclv_value


def _clamp(v: float, lo: float = 1e-6, hi: float = 1.0 - 1e-6) -> float:
    return max(lo, min(hi, v))


def acfl_whatif_projection(scenario: Scenario, inputs: Dict[str, Any], source_state) -> List[Any]:
    """Real deterministic WHAT-IF projection: reads canonical ACFL weights, perturbs m by the
    assumption, and computes EUREKA's gclv_value (ACFL/ELF). The math is delegated to gclv_value."""
    from .projected_artifact import ProjectedArtifact
    weights = source_state.acfl.weights
    s_g = float(weights.get("cost", 50.0)) / 100.0
    base_m = float(weights.get("risk", 50.0)) / 100.0
    delta = sum(float(a.get("delta", 0.0)) for a in scenario.assumptions)
    m = _clamp(base_m + delta)
    return [ProjectedArtifact(
        artifact_id="PRJ-ACFL", artifact_kind="PREDICTION",
        source_state_identity=scenario.source_state_identity,
        provenance=["service:whatif", "acfl", "gclv_value"],
        payload={"gclv": gclv_value(s_g, m), "s_g": s_g, "m": m},
    )]


class ScenarioService:
    """Governed service seam over the Scenario domain. All operations are non-canonical and
    delegate to the authoritative domain components. Optionally persists (bounded, file-backed)."""

    def __init__(self, runtime: Optional[ScenarioRuntime] = None, repository=None,
                 artifact_dir: str = "data/scenario-artifacts") -> None:
        self._runtime = runtime or ScenarioRuntime()
        self._repository = repository
        self._artifact_dir = artifact_dir

    # ---- construction ---------------------------------------------------- #
    def create(self, source_state, *, scenario_id: str = "SCN-1",
               assumptions: Optional[List[Dict[str, Any]]] = None,
               projected_artifacts: Optional[list] = None,
               provenance: Optional[List[str]] = None) -> Scenario:
        """Create a non-canonical Scenario bound to a canonical source (Q2 identity)."""
        return Scenario.from_source(scenario_id, source_state, assumptions=assumptions,
                                    projected_artifacts=projected_artifacts, provenance=provenance)

    def validate_source(self, scenario: Scenario, current_state) -> str:
        """Return MATCH/STALE using Q2 (no service-level identity)."""
        return compare_source_identity(scenario.source_state_identity, current_state)

    def start(self, scenario: Scenario, current_state) -> ScenarioLifecycle:
        """CREATE + READY + RUN (READY validates the scenario/source first)."""
        lc = ScenarioLifecycle.create(scenario).ready(current_state).run()
        return lc

    # ---- lifecycle operations (delegate to ScenarioLifecycle) ------------- #
    def project(self, lifecycle: ScenarioLifecycle, current_state,
                projection_fn: Callable[[Scenario, Dict[str, Any]], List[Any]],
                inputs: Optional[Dict[str, Any]] = None) -> ScenarioLifecycle:
        """PROJECT: delegate to ScenarioLifecycle.project → ScenarioRuntime (DRY_RUN)."""
        return lifecycle.project(current_state, projection_fn, inputs)

    def validate(self, lifecycle: ScenarioLifecycle, current_state) -> ScenarioLifecycle:
        return lifecycle.validate(current_state, runtime=self._runtime)

    def review(self, lifecycle: ScenarioLifecycle) -> ScenarioLifecycle:
        return lifecycle.review()

    def discard(self, lifecycle: ScenarioLifecycle) -> ScenarioLifecycle:
        return lifecycle.discard()

    def authorize(self, lifecycle: ScenarioLifecycle) -> ScenarioLifecycle:
        """AUTHORIZE records a decision; it does NOT execute external effects."""
        return lifecycle.authorize()

    def result_of(self, lifecycle: ScenarioLifecycle) -> Optional[ScenarioRuntimeResult]:
        return lifecycle.runtime_result

    def run_whatif(self, source_state, *, scenario_id: str = "SCN-1",
                   assumptions: Optional[List[Dict[str, Any]]] = None) -> ScenarioRuntimeResult:
        """Governed, WHAT-IF: create → ready → run → project (real ACFL) → validate → review,
        delegating to the domain components. Returns the NON_CANONICAL projected result and, if a
        repository is configured, persists the Scenario + result."""
        sc = self.create(source_state, scenario_id=scenario_id, assumptions=assumptions)
        lc = self.start(sc, source_state)
        lc = self.project(lc, source_state, lambda scen, inputs: real_whatif_projection(scen, inputs, source_state))
        lc = self.validate(lc, source_state)
        lc = self.review(lc)
        if self._repository:
            self._repository.save_scenario(sc)
            self._repository.save_result(lc.runtime_result)
            self._repository.save_lifecycle(lc)
        return lc.runtime_result

    def reproject(self, scenario: Scenario, source_state) -> ScenarioRuntimeResult:
        """Re-run the governed pipeline for an already-created Scenario (e.g. loaded from
        persistence) against a (re-supplied, possibly changed) canonical source. Fail-closed on
        stale source. Persists the resulting ScenarioRuntimeResult."""
        lc = ScenarioLifecycle.create(scenario).ready(source_state).run()
        lc = self.project(lc, source_state, lambda scen, inputs: real_whatif_projection(scen, inputs, source_state))
        lc = self.validate(lc, source_state)
        lc = self.review(lc)
        if self._repository:
            self._repository.save_result(lc.runtime_result)
            self._repository.save_lifecycle(lc)
        return lc.runtime_result

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        return self._repository.get_scenario(scenario_id) if self._repository else None

    def get_result(self, scenario_id: str) -> Optional[ScenarioRuntimeResult]:
        return self._repository.get_result(scenario_id) if self._repository else None

    # ---- human decision workflow (record-only) ----------------------------- #
    def _require_scenario(self, scenario_id: str) -> Scenario:
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        sc = self._repository.get_scenario(scenario_id)
        if sc is None:
            raise ValueError(f"SCENARIO_NOT_FOUND: {scenario_id}")
        return sc

    def _to_review(self, scenario_id: str, source_state) -> ScenarioLifecycle:
        """Reconstruct the governed pipeline through REVIEW from a persisted Scenario, re-validating
        the source identity (fail-closed on stale) so a decision is made against the LATEST canonical
        content. Non-canonical throughout; never mutates canonical state.

        Fail-closed: a Scenario whose recorded lifecycle is already terminal (AUTHORIZED / DISCARDED /
        FAILED) can never be re-opened for review — a decision can be recorded only once."""
        sc = self._require_scenario(scenario_id)
        saved = self._repository.get_lifecycle(scenario_id) if self._repository else None
        if saved is not None and saved.status in (ScenarioLifecycleStatus.AUTHORIZED,
                                                 ScenarioLifecycleStatus.DISCARDED,
                                                 ScenarioLifecycleStatus.FAILED):
            raise LifecycleTransitionError(saved.status.value, "REVIEW")
        lc = ScenarioLifecycle.create(sc).ready(source_state).run()
        lc = self.project(lc, source_state, lambda scen, inputs: real_whatif_projection(scen, inputs, source_state))
        lc = self.validate(lc, source_state)
        lc = self.review(lc)
        if self._repository:
            self._repository.save_lifecycle(lc)
        return lc

    def authorize_scenario(self, scenario_id: str, source_state, decision_type: DecisionType, *,
                           rationale: str = "", human_actor: str = "human",
                           selected_artifact_id: Optional[str] = None) -> ScenarioDecision:
        """REVIEW -> AUTHORIZED. Records an explicit HUMAN decision (record-only): the human confirms
        this non-canonical scenario. It does NOT execute, promote, or canonicalize."""
        sc = self._require_scenario(scenario_id)
        lc = self._to_review(scenario_id, source_state)
        lc = lc.authorize()
        if self._repository:
            self._repository.save_lifecycle(lc)
        decision = ScenarioDecision.record(sc, "AUTHORIZED", decision_type, rationale=rationale,
                                           human_actor=human_actor, selected_artifact_id=selected_artifact_id)
        if self._repository:
            self._repository.save_decision(decision)
        return decision

    def discard_scenario(self, scenario_id: str, source_state, decision_type: Optional[DecisionType] = None, *,
                         rationale: str = "", human_actor: str = "human",
                         selected_artifact_id: Optional[str] = None) -> ScenarioDecision:
        """REVIEW -> DISCARDED. Records the human's (record-only) rejection/discard of the evidence."""
        sc = self._require_scenario(scenario_id)
        lc = self._to_review(scenario_id, source_state)
        lc = lc.discard()
        if self._repository:
            self._repository.save_lifecycle(lc)
        decision = ScenarioDecision.record(sc, "DISCARDED", decision_type or DecisionType.REJECT,
                                           rationale=rationale, human_actor=human_actor,
                                           selected_artifact_id=selected_artifact_id)
        if self._repository:
            self._repository.save_decision(decision)
        return decision

    def get_decision(self, scenario_id: str) -> Optional[ScenarioDecision]:
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        return self._repository.get_decision(scenario_id)

    def list_decisions(self) -> List[ScenarioDecision]:
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        return self._repository.list_decisions()

    # ---- governed ACTION execution (REAL_EXECUTION under Q4) ----------------- #
    def execute_authorized(self, scenario_id: str, source_state, *,
                           boundary=None) -> ScenarioExecution:
        """Execute the single action that a recorded HUMAN decision authorizes.

        Fail-closed chain: scenario exists -> decision exists -> not already executed (idempotent)
        -> Q2 source is current (NOT stale) -> action resolves -> Q4 (classifier + policy under
        REAL_EXECUTION) -> REAL observable effect (governed artifact write) -> execution record.

        Never mutates the Scenario, never promotes/canonicalizes, never fabricates success.
        """
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        sc = self._require_scenario(scenario_id)
        decision = self._repository.get_decision(scenario_id)
        if decision is None:
            raise ValueError(f"DECISION_NOT_FOUND: {scenario_id}")
        # idempotency: a (scenario_id, decision_id) executes at most once (no duplicate effect)
        existing = self._repository.get_execution(scenario_id)
        if existing is not None:
            return existing
        # Q2 stale protection BEFORE any effect (authorization does not bypass identity control)
        if compare_source_identity(sc.source_state_identity, source_state) != "MATCH":
            rejected = ScenarioExecution.record(
                scenario=sc, decision=decision, action_id="NONE",
                status=ScenarioExecutionStatus.REJECTED,
                governance={"mode": "REAL_EXECUTION", "effect_class": "MUTATE",
                            "decision": "BLOCK", "reason_code": "STALE_SOURCE",
                            "message": "scenario source identity does not match current canonical state"},
                effect={})
            self._repository.save_execution(rejected)
            return rejected
        result = self.get_result(scenario_id)
        pa = list(result.projected_artifacts) if result and result.projected_artifacts else None
        execution = execute_gov(decision, sc, source_state, self._artifact_dir,
                                boundary=boundary or default_boundary(), projected_artifacts=pa)
        self._repository.save_execution(execution)
        return execution

    def get_execution(self, scenario_id: str) -> Optional[ScenarioExecution]:
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        return self._repository.get_execution(scenario_id)

    def list_executions(self) -> List[ScenarioExecution]:
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        return self._repository.list_executions()

    def audit(self, scenario_id: str, work_id: Optional[str] = None, work_resolver=None):
        """READ-ONLY observability projection: assemble the durable audit trail for a Scenario from
        the existing authorities (WorkStore + ScenarioRepository). Never writes / mutates / authorizes.
        """
        from .scenario_observability import build_audit
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        return build_audit(self._repository, work_resolver, scenario_id, work_id)

    def compare(self, scenario_ids, baseline_scenario_id: Optional[str] = None):
        """Aggregate persisted results (evidence only, non-canonical). Delegates to the pure
        comparison function; read-only, never recommends/promotes."""
        from .scenario_comparison import compare_results
        if not self._repository:
            raise RuntimeError("REPOSITORY_NOT_CONFIGURED")
        return compare_results(self._repository, list(scenario_ids), baseline_scenario_id)

    @property
    def runtime(self) -> ScenarioRuntime:
        return self._runtime
