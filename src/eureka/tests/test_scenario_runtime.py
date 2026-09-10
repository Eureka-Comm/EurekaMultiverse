"""LS-SCN-R1 — Scenario Runtime tests (scenario_runtime.py)."""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass
from src.eureka.universe.scenario_foundation import Scenario
from src.eureka.universe.scenario_runtime import ScenarioRuntime, ScenarioRuntimeResult, SCENARIO_PROJECTION_CAPABILITY
from src.eureka.universe.effect_policy import EffectClass, ExecutionMode, DryRunContext, PolicyError, default_boundary


def mk(work_id="W1", with_result=False):
    state = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="t", user_intent="u", task_category="c", problem_statement="p"))
    if with_result:
        from src.eureka.universe.canonical_state import WorkResult
        state.result = WorkResult(result_id="RES-1", work_id=work_id, status="AVAILABLE", summary="done")
    return state


def test_runtime_projects_hypothetical_in_dry_run():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    rt = ScenarioRuntime()

    def projection(scenario, inputs):
        return [ProjectedArtifact.from_source("PRJ-1", "PREDICTION", s)]

    result = rt.project(sc, s, projection)
    assert isinstance(result, ScenarioRuntimeResult)
    assert result.is_non_canonical is True
    assert result.scope == ArtifactScope.SCENARIO
    assert result.authority == AuthorityClass.PROJECTED
    assert result.projected_artifacts[0].is_non_canonical is True
    assert result.provenance


def test_runtime_rejects_stale_source_fail_closed():
    s = mk(with_result=False)
    sc = Scenario.from_source("SCN-1", s)
    rt = ScenarioRuntime()
    changed = mk(with_result=True)

    def projection(scenario, inputs):
        return []

    with pytest.raises(RuntimeError) as exc:
        rt.project(sc, changed, projection)
    assert "STALE_SOURCE" in str(exc.value)


def test_runtime_does_not_mutate_canonical_state():
    s = mk(with_result=True)
    fp_before = canonical_state_fingerprint(s)
    sc = Scenario.from_source("SCN-1", s)
    rt = ScenarioRuntime()

    def projection(scenario, inputs):
        return [ProjectedArtifact.from_source("PRJ-1", "PREDICTION", s)]

    rt.project(sc, s, projection)
    assert canonical_state_fingerprint(s) == fp_before
    assert s.revision == 1


def test_runtime_projection_capability_is_compute():
    b = default_boundary()
    assert b.classifier.effect_for(SCENARIO_PROJECTION_CAPABILITY) == EffectClass.UNKNOWN  # before classify
    rt = ScenarioRuntime()
    assert rt._boundary.classifier.effect_for(SCENARIO_PROJECTION_CAPABILITY) == EffectClass.COMPUTE


def test_runtime_effect_boundary_blocks_mutate_in_dry_run():
    # a MUTATE capability in DRY_RUN is still blocked by the reused Q4 boundary (no projection runs)
    b = default_boundary()
    b.classify("mutate_cap", EffectClass.MUTATE)
    ctx = DryRunContext(capability_id="mutate_cap", target="X", mode=ExecutionMode.DRY_RUN)
    called = {"n": 0}
    with pytest.raises(PolicyError):
        b.execute(ctx, lambda: called.__setitem__("n", 1))
    assert called["n"] == 0


def test_runtime_serializes_non_canonical_result():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    rt = ScenarioRuntime()

    def projection(scenario, inputs):
        return [ProjectedArtifact.from_source("PRJ-1", "PREDICTION", s)]

    result = rt.project(sc, s, projection)
    reloaded = ScenarioRuntimeResult.model_validate(result.model_dump(mode="json"))
    assert reloaded.is_non_canonical is True
    assert reloaded.scope == ArtifactScope.SCENARIO
    assert reloaded.projected_artifacts[0].source_state_identity == result.projected_artifacts[0].source_state_identity
