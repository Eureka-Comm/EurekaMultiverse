"""LS-SCN-R2 — Scenario Lifecycle tests (scenario_lifecycle.py)."""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass
from src.eureka.universe.scenario_foundation import Scenario
from src.eureka.universe.scenario_runtime import ScenarioRuntime
from src.eureka.universe.scenario_lifecycle import (
    ScenarioLifecycle, ScenarioLifecycleStatus, LifecycleTransitionError,
)


def mk(work_id="W1", with_result=False):
    state = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="t", user_intent="u", task_category="c", problem_statement="p"))
    if with_result:
        from src.eureka.universe.canonical_state import WorkResult
        state.result = WorkResult(result_id="RES-1", work_id=work_id, status="AVAILABLE", summary="done")
    return state


def proj(scenario, inputs, source):
    return [ProjectedArtifact.from_source("PRJ-1", "PREDICTION", source)]


def test_create_lifecycle_starts_non_canonical():
    s = mk(with_result=True)
    lc = ScenarioLifecycle.create(Scenario.from_source("SCN-1", s))
    assert lc.status == ScenarioLifecycleStatus.CREATED
    assert lc.is_non_canonical is True


def test_valid_path_ready_run_project_validate_review():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    lc = ScenarioLifecycle.create(sc).ready(s).run()
    lc.project(s, lambda scen, inputs: proj(scen, inputs, s))
    lc.validate(s).review()
    assert lc.status == ScenarioLifecycleStatus.REVIEW
    assert lc.runtime_result.is_non_canonical is True
    assert lc.runtime_result.projected_artifacts[0].authority == AuthorityClass.PROJECTED


def test_discard_is_terminal_fail_closed():
    s = mk(with_result=True)
    lc = ScenarioLifecycle.create(Scenario.from_source("SCN-1", s)).ready(s).run()
    lc.project(s, lambda scen, inputs: proj(scen, inputs, s)).validate(s).review().discard()
    assert lc.status == ScenarioLifecycleStatus.DISCARDED
    with pytest.raises(LifecycleTransitionError):
        lc.run()  # DISCARD -> RUN invalid


def test_authorize_records_but_does_not_execute():
    s = mk(with_result=True)
    lc = ScenarioLifecycle.create(Scenario.from_source("SCN-1", s)).ready(s).run()
    lc.project(s, lambda scen, inputs: proj(scen, inputs, s)).validate(s).review().authorize()
    assert lc.status == ScenarioLifecycleStatus.AUTHORIZED
    # authorize must NOT expose any external-execution method
    for attr in ("execute", "run_external", "promote", "schedule"):
        assert not hasattr(lc, attr)


def test_invalid_transitions_fail_closed():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    lc = ScenarioLifecycle.create(sc)
    for bad in (ScenarioLifecycleStatus.REVIEW, ScenarioLifecycleStatus.PROJECTED):
        with pytest.raises(LifecycleTransitionError):
            lc.transition(bad)  # CREATE -> REVIEW / PROJECT invalid
    # READY -> REVIEW invalid
    lc.ready(s)
    with pytest.raises(LifecycleTransitionError):
        lc.transition(ScenarioLifecycleStatus.REVIEW)
    # REVIEW -> PROJECT invalid (needs full path)
    lc2 = ScenarioLifecycle.create(sc).ready(s).run()
    lc2.project(s, lambda scen, inputs: proj(scen, inputs, s)).validate(s).review()
    with pytest.raises(LifecycleTransitionError):
        lc2.transition(ScenarioLifecycleStatus.PROJECTED)


def test_stale_source_fails_closed_on_validate():
    s = mk(with_result=False)
    sc = Scenario.from_source("SCN-1", s)
    lc = ScenarioLifecycle.create(sc).ready(s).run()
    lc.project(s, lambda scen, inputs: proj(scen, inputs, s))
    changed = mk(with_result=True)
    with pytest.raises(LifecycleTransitionError):
        lc.validate(changed)  # stale source -> not MATCH -> fail closed


def test_canonical_state_unchanged_through_lifecycle():
    s = mk(with_result=True)
    fp_before = canonical_state_fingerprint(s)
    lc = ScenarioLifecycle.create(Scenario.from_source("SCN-1", s)).ready(s).run()
    lc.project(s, lambda scen, inputs: proj(scen, inputs, s)).validate(s).review()
    assert canonical_state_fingerprint(s) == fp_before
    assert s.revision == 1


def test_serialization_preserves_governance_and_identity():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    lc = ScenarioLifecycle.create(sc).ready(s).run()
    lc.project(s, lambda scen, inputs: proj(scen, inputs, s)).validate(s).review()
    dumped = lc.model_dump(mode="json")
    reloaded = ScenarioLifecycle.model_validate(dumped)
    assert reloaded.status == ScenarioLifecycleStatus.REVIEW
    assert reloaded.scenario.source_state_identity == sc.source_state_identity
    assert reloaded.runtime_result.is_non_canonical is True
    assert reloaded.is_non_canonical is True


def test_prediction_scenario_untouched():
    # PredictionScenario remains a separate, constructible predictor-specific structure
    from src.eureka.universe.canonical_state import PredictionScenario
    ps = PredictionScenario(scenario_id="PSC-1", name="n", assumptions=["x"], perturbed_variables={"a": 1})
    assert ps.scenario_id == "PSC-1"
    # Scenario lifecycle is bound to Scenario (foundation), never to PredictionScenario
    assert type(ps) is not Scenario
