"""LS-WHATIF-ACFL — What-If over EUREKA's real deterministic ACFL/MathEngine computation.

Proves the governed WHAT-IF pipeline can execute a REAL deterministic EUREKA computation
(``gclv_value`` — the ACFL/ELF base, ``acfl_engine.py``) under hypothetical assumptions, while
remaining DRY_RUN, NON_CANONICAL, provenance-aware and fail-closed.

Inputs come from the canonical ``ACFLState.weights``; the assumption perturbs the hypothetical
``m`` input; ``gclv_value(s_g, m_assumed)`` computes the deterministic projection.
"""
import pytest
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.acfl_engine import gclv_value
from src.eureka.universe.projected_artifact import ProjectedArtifact, ArtifactScope, AuthorityClass
from src.eureka.universe.scenario_foundation import Scenario
from src.eureka.universe.scenario_lifecycle import ScenarioLifecycle, ScenarioLifecycleStatus, LifecycleTransitionError


def source_acfl(risk=50.0, cost=50.0):
    state = CanonicalWorkState(work=EurekaWork(
        work_id="W1", title="t", user_intent="u", task_category="c", problem_statement="p"))
    state.acfl.weights = {"cost": float(cost), "risk": float(risk)}
    return state


def _clamp(v, lo=1e-6, hi=1.0 - 1e-6):
    return max(lo, min(hi, v))


def projection_acfl(scenario, inputs, source):
    # Real inputs derived from canonical ACFL weights; assumption perturbs the hypothetical m.
    weights = source.acfl.weights
    s_g = float(weights.get("cost", 50.0)) / 100.0
    base_m = float(weights.get("risk", 50.0)) / 100.0
    delta = sum(float(a.get("delta", 0.0)) for a in scenario.assumptions)
    m_assumed = _clamp(base_m + delta)
    value = gclv_value(s_g, m_assumed)   # EUREKA's real deterministic math
    return [ProjectedArtifact(
        artifact_id="PRJ-ACFL", artifact_kind="PREDICTION",
        source_state_identity=scenario.source_state_identity,
        provenance=["scenario:SCN-1", "whatif:acfl", "gclv_value"],
        payload={"gclv": value, "s_g": s_g, "m": m_assumed},
    )]


def run_acfl(risk=50.0, delta=0.0):
    src = source_acfl(risk=risk)
    sc = Scenario.from_source("SCN-1", src, assumptions=[{"delta": delta}])
    lc = (ScenarioLifecycle.create(sc).ready(src).run()
          .project(src, lambda scen, inputs: projection_acfl(scen, inputs, src))
          .validate(src).review())
    return src, sc, lc


def test_real_acfl_gclv_math_invoked():
    src, _, lc = run_acfl(risk=50.0, delta=0.1)
    pa = lc.runtime_result.projected_artifacts[0]
    expected = gclv_value(0.5, _clamp(0.5 + 0.1))
    assert pa.payload["gclv"] == expected          # equals the real function's output, not a mock


def test_valid_scenario_acfl_projected_result():
    src, _, lc = run_acfl(risk=50.0, delta=0.1)
    assert lc.status == ScenarioLifecycleStatus.REVIEW
    assert lc.runtime_result.is_non_canonical is True
    assert lc.runtime_result.projected_artifacts[0].payload["gclv"] is not None


def test_assumption_changes_real_computation():
    _, _, lc0 = run_acfl(50.0, 0.0)
    _, _, lc1 = run_acfl(50.0, 0.2)
    assert lc0.runtime_result.projected_artifacts[0].payload["m"] == 0.5
    assert lc1.runtime_result.projected_artifacts[0].payload["m"] == 0.7
    assert lc0.runtime_result.projected_artifacts[0].payload["gclv"] != lc1.runtime_result.projected_artifacts[0].payload["gclv"]


def test_identical_input_is_deterministic():
    _, _, a = run_acfl(50.0, 0.1)
    _, _, b = run_acfl(50.0, 0.1)
    assert a.runtime_result.projected_artifacts[0].payload["gclv"] == b.runtime_result.projected_artifacts[0].payload["gclv"]


def test_result_is_non_canonical():
    src, sc, lc = run_acfl(50.0, 0.1)
    pa = lc.runtime_result.projected_artifacts[0]
    assert pa.authority == AuthorityClass.PROJECTED
    assert pa.scope == ArtifactScope.SCENARIO
    assert pa.is_non_canonical is True
    assert lc.runtime_result.is_non_canonical is True
    assert sc.is_non_canonical is True


def test_source_identity_uses_q2():
    src, sc, _ = run_acfl(50.0, 0.1)
    assert sc.source_state_identity == canonical_state_fingerprint(src)


def test_stale_source_fails_closed():
    src_a = source_acfl(50.0)
    sc = Scenario.from_source("SCN-1", src_a, assumptions=[{"delta": 0.1}])
    lc = ScenarioLifecycle.create(sc).ready(src_a).run()
    lc.project(src_a, lambda scen, inputs: projection_acfl(scen, inputs, src_a))
    # a change to a fingerprint-relevant canonical field (result) makes the source STALE
    from src.eureka.universe.canonical_state import WorkResult
    src_b = source_acfl(80.0)
    src_b.result = WorkResult(result_id="R2", work_id="W1", status="AVAILABLE", summary="x")
    with pytest.raises((RuntimeError, LifecycleTransitionError)):
        lc.validate(src_b)


def test_canonical_state_unchanged():
    src, _, _ = run_acfl(50.0, 0.1)
    assert src.revision == 1
    assert src.acfl.weights == {"cost": 50.0, "risk": 50.0}
