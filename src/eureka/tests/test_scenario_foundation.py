"""LS-Q1 — Scenario Foundation Separation tests (scenario_foundation.py)."""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, PredictionScenario
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass
from src.eureka.universe.scenario_foundation import Scenario, ScenarioStatus


def mk(work_id="W1", with_result=False):
    state = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="t", user_intent="u", task_category="c", problem_statement="p"))
    if with_result:
        from src.eureka.universe.canonical_state import WorkResult
        state.result = WorkResult(result_id="RES-1", work_id=work_id, status="AVAILABLE", summary="done")
    return state


def test_scenario_creation_non_canonical():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    assert sc.is_non_canonical is True
    assert sc.scope == ArtifactScope.SCENARIO
    assert sc.status == ScenarioStatus.HYPOTHETICAL


def test_scenario_source_identity_reuses_q2():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    assert sc.source_state_identity == canonical_state_fingerprint(s)


def test_scenario_requires_source_identity():
    with pytest.raises(ValueError):
        Scenario(scenario_id="x", source_state_identity="", provenance=["p"])


def test_scenario_requires_provenance():
    with pytest.raises(ValueError):
        Scenario(scenario_id="x", source_state_identity="h", provenance=[])


def test_scenario_stores_assumptions():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s, assumptions=[{"var": "cost", "delta": 10}])
    assert len(sc.assumptions) == 1
    assert sc.assumptions[0]["var"] == "cost"


def test_scenario_cannot_be_canonical_implicitly():
    with pytest.raises(ValueError):
        Scenario(scenario_id="x", source_state_identity="h", provenance=["p"],
                 scope=ArtifactScope.CANONICAL)


def test_scenario_references_projected_artifact_preserving_authority():
    s = mk(with_result=True)
    pa = ProjectedArtifact.from_source("PRJ-1", "PREDICTION", s)
    sc = Scenario.from_source("SCN-1", s, projected_artifacts=[pa])
    assert sc.projected_artifacts[0].authority == AuthorityClass.PROJECTED
    assert sc.projected_artifacts[0].scope == ArtifactScope.SCENARIO
    assert sc.projected_artifacts[0].is_non_canonical is True


def test_stale_source_detectable():
    s = mk(with_result=False)
    sc = Scenario.from_source("SCN-1", s)
    assert sc.verify_source(s) == "MATCH"
    changed = mk(with_result=True)
    assert sc.verify_source(changed) == "STALE"


def test_canonical_state_unchanged_after_scenario_creation_and_validation():
    s = mk(with_result=True)
    fp_before = canonical_state_fingerprint(s)
    sc = Scenario.from_source("SCN-1", s)
    Scenario.model_validate(sc.model_dump(mode="json"))
    assert canonical_state_fingerprint(s) == fp_before
    assert s.revision == 1


def test_serialization_roundtrip_preserves_governance():
    s = mk(with_result=True)
    pa = ProjectedArtifact.from_source("PRJ-1", "PREDICTION", s)
    sc = Scenario.from_source("SCN-1", s, assumptions=[{"a": 1}], projected_artifacts=[pa])
    dumped = sc.model_dump(mode="json")
    reloaded = Scenario.model_validate(dumped)
    assert reloaded.scenario_id == sc.scenario_id
    assert reloaded.source_state_identity == sc.source_state_identity
    assert reloaded.scope == ArtifactScope.SCENARIO
    assert reloaded.provenance == sc.provenance
    assert reloaded.assumptions == sc.assumptions
    assert reloaded.projected_artifacts[0].source_state_identity == pa.source_state_identity


def test_prediction_scenario_preserved_and_distinct():
    # PredictionScenario still exists and is constructible (unchanged semantics)
    ps = PredictionScenario(scenario_id="PSC-1", name="n", assumptions=["x"], perturbed_variables={"a": 1})
    assert ps.scenario_id == "PSC-1"
    assert ps.name == "n"
    # Scenario and PredictionScenario are distinct types; a PredictionScenario does not validate as Scenario
    assert type(ps) is not Scenario
    with pytest.raises(ValueError):
        # PredictionScenario-shaped data lacks source_state_identity/provenance -> rejected as Scenario
        Scenario(**{"scenario_id": "PSC-1", "assumptions": ["x"], "perturbed_variables": {"a": 1}})


def test_no_execution_api_on_scenario():
    s = mk(with_result=True)
    sc = Scenario.from_source("SCN-1", s)
    for attr in ("execute", "run", "simulate", "promote", "schedule", "evaluate"):
        assert not hasattr(sc, attr), f"Scenario must not expose execution API: {attr}"


def test_malformed_scenario_rejected():
    with pytest.raises(ValueError):
        Scenario(scenario_id="x", source_state_identity="h", provenance=["p"],
                 status="CANONICAL")  # not a valid ScenarioStatus value
