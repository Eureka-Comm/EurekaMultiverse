"""LS-SCN-SVC — Scenario Service Surface tests (scenario_service.py)."""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, WorkResult
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.acfl_engine import gclv_value
from src.eureka.universe.projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass
from src.eureka.universe.scenario_lifecycle import ScenarioLifecycleStatus, LifecycleTransitionError
from src.eureka.universe.scenario_service import ScenarioService


def src_with_acfl(risk=50.0, cost=50.0):
    state = CanonicalWorkState(work=EurekaWork(
        work_id="W1", title="t", user_intent="u", task_category="c", problem_statement="p"))
    state.acfl.weights = {"cost": float(cost), "risk": float(risk)}
    return state


def _clamp(v, lo=1e-6, hi=1.0 - 1e-6):
    return max(lo, min(hi, v))


def acfl_projection(scenario, inputs, source):
    weights = source.acfl.weights
    s_g = float(weights["cost"]) / 100.0
    base_m = float(weights["risk"]) / 100.0
    delta = sum(float(a.get("delta", 0.0)) for a in scenario.assumptions)
    m = _clamp(base_m + delta)
    return [ProjectedArtifact(
        artifact_id="PRJ-ACFL", artifact_kind="PREDICTION",
        source_state_identity=scenario.source_state_identity,
        provenance=["service:project", "whatif:acfl"],
        payload={"gclv": gclv_value(s_g, m), "s_g": s_g, "m": m},
    )]


def test_create_scenario_through_service():
    svc = ScenarioService()
    src = src_with_acfl()
    sc = svc.create(src, scenario_id="SCN-1", assumptions=[{"delta": 0.1}])
    assert sc.is_non_canonical is True
    assert sc.assumptions == [{"delta": 0.1}]
    assert sc.source_state_identity == canonical_state_fingerprint(src)


def test_valid_lifecycle_through_service():
    svc = ScenarioService()
    src = src_with_acfl()
    sc = svc.create(src, scenario_id="SCN-1", assumptions=[{"delta": 0.1}])
    lc = svc.start(sc, src)
    lc = svc.project(lc, src, lambda scen, inputs: acfl_projection(scen, inputs, src))
    lc = svc.validate(lc, src)
    lc = svc.review(lc)
    assert lc.status == ScenarioLifecycleStatus.REVIEW


def test_assumptions_reach_projection_through_service():
    svc = ScenarioService()
    src = src_with_acfl(risk=50.0)
    sc = svc.create(src, scenario_id="SCN-1", assumptions=[{"delta": 0.2}])
    lc = svc.start(sc, src)
    lc = svc.project(lc, src, lambda scen, inputs: acfl_projection(scen, inputs, src))
    assert lc.runtime_result.projected_artifacts[0].payload["m"] == 0.7


def test_real_deterministic_computation_reachable_through_service():
    svc = ScenarioService()
    src = src_with_acfl(risk=50.0)
    sc = svc.create(src, assumptions=[{"delta": 0.1}])
    lc = svc.start(sc, src)
    lc = svc.project(lc, src, lambda scen, inputs: acfl_projection(scen, inputs, src))
    pa = lc.runtime_result.projected_artifacts[0]
    assert pa.payload["gclv"] == gclv_value(0.5, _clamp(0.5 + 0.1))  # real ACFL math


def test_projected_output_non_canonical_and_authority_preserved():
    svc = ScenarioService()
    src = src_with_acfl()
    sc = svc.create(src, assumptions=[{"delta": 0.1}])
    lc = svc.start(sc, src)
    lc = svc.project(lc, src, lambda scen, inputs: acfl_projection(scen, inputs, src))
    lc = svc.validate(lc, src)
    lc = svc.review(lc)
    pa = lc.runtime_result.projected_artifacts[0]
    assert pa.authority == AuthorityClass.PROJECTED
    assert pa.scope == ArtifactScope.SCENARIO
    assert pa.is_non_canonical is True
    assert lc.is_non_canonical is True


def test_q2_identity_and_provenance_preserved_through_service():
    svc = ScenarioService()
    src = src_with_acfl()
    sc = svc.create(src, assumptions=[{"delta": 0.1}])
    assert sc.source_state_identity == canonical_state_fingerprint(src)
    assert sc.provenance  # provenance present


def test_stale_source_fails_closed_through_service():
    svc = ScenarioService()
    src_a = src_with_acfl(risk=50.0)
    sc = svc.create(src_a, assumptions=[{"delta": 0.1}])
    lc = svc.start(sc, src_a)
    lc = svc.project(lc, src_a, lambda scen, inputs: acfl_projection(scen, inputs, src_a))
    src_b = src_with_acfl(risk=80.0)
    src_b.result = WorkResult(result_id="R2", work_id="W1", status="AVAILABLE", summary="x")
    with pytest.raises((RuntimeError, LifecycleTransitionError)):
        svc.validate(lc, src_b)


def test_canonical_state_unchanged_through_service():
    svc = ScenarioService()
    src = src_with_acfl()
    fp_before = canonical_state_fingerprint(src)
    sc = svc.create(src, assumptions=[{"delta": 0.1}])
    lc = svc.start(sc, src)
    lc = svc.project(lc, src, lambda scen, inputs: acfl_projection(scen, inputs, src))
    lc = svc.validate(lc, src).review()
    assert canonical_state_fingerprint(src) == fp_before
    assert src.revision == 1


def test_invalid_lifecycle_operation_fails_closed():
    svc = ScenarioService()
    src = src_with_acfl()
    sc = svc.create(src, assumptions=[{"delta": 0.1}])
    lc = svc.start(sc, src)
    with pytest.raises(LifecycleTransitionError):
        svc.review(lc)  # RUNNING -> REVIEW is invalid


def test_service_has_no_execution_api():
    svc = ScenarioService()
    for attr in ("execute", "promote", "schedule", "simulate_distributed", "publish_canonical", "execute_real_world"):
        assert not hasattr(svc, attr), f"ScenarioService must not expose {attr}"


def test_authorize_does_not_execute_external_effects():
    svc = ScenarioService()
    src = src_with_acfl()
    sc = svc.create(src, assumptions=[{"delta": 0.1}])
    lc = svc.start(sc, src)
    lc = svc.project(lc, src, lambda scen, inputs: acfl_projection(scen, inputs, src))
    lc = svc.validate(lc, src).review()
    lc = svc.authorize(lc)
    assert lc.status == ScenarioLifecycleStatus.AUTHORIZED
    for attr in ("execute", "promote", "schedule"):
        assert not hasattr(lc, attr)
