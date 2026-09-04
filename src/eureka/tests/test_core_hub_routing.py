"""Core-hub specialist routing (Phase B) — no rank-based auto-chain, Core controls next-owner.

EUREKA 5.1: "El siguiente paso requiere asignación/autorización de EM Core."
`_normalize_em_pipeline_order` must be a pure technical ordering normalizer (drops backward
edges to prevent cycles) and must NOT inject dependencies by EM rank — because step presence +
dependency satisfaction is a PREREQUISITE, not an AUTHORIZATION for the next EM. Core (the runtime
`advance` loop) drives the order following the task network's explicit dependencies.
"""
import pytest

from src.eureka.universe.orchestrator import (
    WorkOrchestrator,
    _guard_no_silent_decision_omission,
    _detect_operation_mode,
)
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.canonical_state import ExecutionPlan, ExecutionStep
from src.eureka.universe.problem_model import StructuredProblem, TaskNetwork
from src.eureka.universe.cognitive_engine import TestDoubleCognitiveEngine


def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _wo() -> WorkOrchestrator:
    return WorkOrchestrator(_reg(), TestDoubleCognitiveEngine())


def _step(sid, em, deps=None):
    return ExecutionStep(
        step_id=sid, capability_id="cap_" + sid, target=f"EM[{em}]", canonical_em=em,
        status="PENDING", dependencies=deps or [], expected_outputs=[], produces_result=False,
    )


def _sp() -> StructuredProblem:
    sp = StructuredProblem(
        questions=[], entities=[], variables=[], relationships=[], assumptions=[],
        unknowns=[], evidence_requirements=[], constraints=[], success_criteria=[],
    )
    sp.task_network = TaskNetwork(tasks=[])
    return sp


# --- No rank-based auto-chain ---
def test_normalize_does_not_add_rank_dependencies():
    wo = _wo()
    plan = ExecutionPlan()
    # six EMs with NO explicit dependencies. A rank-based normalizer would inject all
    # lower-rank steps as prerequisites; the Core-hub normalizer must NOT.
    for sid, em in [
        ("desc", "EM Descriptor"), ("pred", "EM Predictor"), ("presc", "EM Prescriptor"),
        ("act", "EM Actioner"), ("inst", "EM Installer"), ("pub", "EM Publisher"),
    ]:
        plan.steps.append(_step(sid, em))

    wo._normalize_em_pipeline_order(plan)

    for s in plan.steps:
        assert s.dependencies == [], f"rank auto-chain injected deps for {s.canonical_em}"


def test_normalize_drops_backward_edge():
    wo = _wo()
    plan = ExecutionPlan()
    plan.steps.append(_step("desc", "EM Descriptor"))
    plan.steps.append(_step("act", "EM Actioner"))
    # Prescriptor explicitly depends on a higher-rank EM (Actioner) -> backward edge -> must be dropped
    plan.steps.append(_step("presc", "EM Prescriptor", deps=["act"]))

    wo._normalize_em_pipeline_order(plan)

    presc = next(s for s in plan.steps if s.canonical_em == "EM Prescriptor")
    assert "act" not in (presc.dependencies or [])  # cyclic/backward edge removed


def test_normalize_keeps_explicit_forward_dependency():
    wo = _wo()
    plan = ExecutionPlan()
    plan.steps.append(_step("desc", "EM Descriptor"))
    plan.steps.append(_step("pub", "EM Publisher", deps=["desc"]))

    wo._normalize_em_pipeline_order(plan)

    pub = next(s for s in plan.steps if s.canonical_em == "EM Publisher")
    assert "desc" in (pub.dependencies or [])  # explicit forward prerequisite kept


# --- Regressions (67d3824 routing + 81c65a3 guard) ---
def test_declarative_analysis_is_decision():
    assert _detect_operation_mode(
        "Analizar el comportamiento de ventas y detectar los principales patrones.", "REPORT") == "DECISION"
    assert _detect_operation_mode("Genera un reporte de ventas.", "REPORT") == "KNOWLEDGE_ANSWER"


def test_guard_no_forced_chain_and_conditional_actioner():
    cr, sp = _reg(), _sp()
    plan = ExecutionPlan()
    plan.steps.append(_step("desc", "EM Descriptor"))
    plan.steps.append(_step("pub", "EM Publisher"))
    _guard_no_silent_decision_omission(plan, type("P", (), {"alternatives": ["a", "b"]})(), sp, "DECISION", cr)
    ems = {s.canonical_em for s in plan.steps}
    assert "EM Prescriptor" in ems
    assert "EM Actioner" not in ems
    assert "EM Installer" not in ems
