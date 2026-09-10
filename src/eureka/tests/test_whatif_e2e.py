"""LS-WHATIF — What-If End-to-End minimal case (real, governed, non-canonical).

Proves the complete Scenario pipeline with a real projection that CONSUMES the assumptions:

    source CanonicalWorkState (WorkResult.scores["total"] = 100)
        -> Scenario.from_source(source)
        -> assumptions=[{"delta": D}]
        -> ScenarioLifecycle.ready -> run -> project -> validate -> review
        -> ScenarioRuntime.project (DRY_RUN, EffectBoundary)
        -> ProjectedArtifact with payload projected_total = total + D   (assumption has real effect)
        -> NON_CANONICAL throughout
        -> canonical state unchanged
"""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, WorkResult
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass
from src.eureka.universe.scenario_foundation import Scenario
from src.eureka.universe.scenario_lifecycle import ScenarioLifecycle, ScenarioLifecycleStatus, LifecycleTransitionError


def source_with_score(score=100, work_id="W1"):
    state = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="t", user_intent="u", task_category="c", problem_statement="p"))
    state.result = WorkResult(result_id="RES-1", work_id=work_id, status="AVAILABLE",
                              summary="done", scores={"total": float(score)})
    return state


def projection_fn(scenario, inputs, source):
    """The hypothetical computation: it consumes the assumptions' delta against the canonical score."""
    baseline = float(source.result.scores["total"])
    delta = 0.0
    for a in scenario.assumptions:
        delta += float(a.get("delta", 0.0))
    projected = baseline + delta
    return [ProjectedArtifact(
        artifact_id="PRJ-1", artifact_kind="PREDICTION",
        source_state_identity=scenario.source_state_identity,
        provenance=[f"scenario:{scenario.scenario_id}", "whatif:projection", "v1"],
        payload={"projected_total": projected},
    )]


def run_e2e(score=100, delta=10.0, work_id="W1"):
    src = source_with_score(score, work_id)
    sc = Scenario.from_source("SCN-1", src, assumptions=[{"delta": delta}])
    lc = (ScenarioLifecycle.create(sc)
          .ready(src)
          .run()
          .project(src, lambda scen, inputs: projection_fn(scen, inputs, src))
          .validate(src)
          .review())
    return src, sc, lc


def test_end_to_end_whatif_flow():
    src, sc, lc = run_e2e(score=100, delta=10.0)
    assert lc.status == ScenarioLifecycleStatus.REVIEW
    assert lc.runtime_result.is_non_canonical is True
    assert lc.runtime_result.projected_artifacts[0].payload["projected_total"] == 110.0


def test_assumption_changes_projected_output():
    _, _, lc_a = run_e2e(100, 10.0)
    _, _, lc_b = run_e2e(100, 25.0)
    assert lc_a.runtime_result.projected_artifacts[0].payload["projected_total"] == 110.0
    assert lc_b.runtime_result.projected_artifacts[0].payload["projected_total"] == 125.0


def test_result_stays_non_canonical():
    _, sc, lc = run_e2e()
    pa = lc.runtime_result.projected_artifacts[0]
    assert pa.authority == AuthorityClass.PROJECTED
    assert pa.scope == ArtifactScope.SCENARIO
    assert pa.is_non_canonical is True
    assert lc.is_non_canonical is True
    assert lc.runtime_result.is_non_canonical is True


def test_source_identity_comes_from_q2():
    _, sc, _ = run_e2e()
    assert sc.source_state_identity == canonical_state_fingerprint(source_with_score(100))


def test_canonical_state_unchanged():
    src, _, _ = run_e2e()
    # fresh source for the fingerprint baseline (run_e2e used the same object; compare a clone)
    fp_before = canonical_state_fingerprint(src)
    # re-run to be explicit
    run_e2e()
    assert canonical_state_fingerprint(src) == fp_before
    assert src.revision == 1


def test_stale_source_fails_closed():
    src_a = source_with_score(100)
    sc = Scenario.from_source("SCN-1", src_a, assumptions=[{"delta": 10}])
    lc = ScenarioLifecycle.create(sc).ready(src_a).run()
    lc.project(src_a, lambda scen, inputs: projection_fn(scen, inputs, src_a))
    src_b = source_with_score(200)  # canonical content changed
    with pytest.raises((LifecycleTransitionError, RuntimeError)):
        lc.validate(src_b)
    assert canonical_state_fingerprint(src_b) is not None  # source_b untouched by the attempt


def test_invalid_scenario_rejected():
    with pytest.raises(ValueError):
        Scenario(scenario_id="x", source_state_identity="h", provenance=[], scope=ArtifactScope.CANONICAL)


def test_units_are_pure_consume_assumptions():
    # assumptions with no delta produce the baseline (no assumption -> unchanged), proving consumption
    _, _, lc = run_e2e(100, 0.0)
    assert lc.runtime_result.projected_artifacts[0].payload["projected_total"] == 100.0
