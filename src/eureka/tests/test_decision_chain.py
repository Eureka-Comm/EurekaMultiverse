"""Task-driven decision routing (orchestrator._guard_no_silent_decision_omission).

EUREKA 5.1: Descriptor/Predictor/Prescriptor "según dependencias"; Actioner "cuando exista
prescripción validada"; Installer "cuando se requiera sistema"; Publisher "cuando se requiera
comunicación"; "El siguiente paso requiere asignación/autorización de EM Core".
So DECISION is NOT a fixed chain. Python only guards against a SILENT omission of a genuinely
required task (the prescription stage) when the problem has concrete alternatives, and NEVER
auto-adds Predictor / Actioner / Installer / Publisher.
"""
import pytest

from src.eureka.universe.orchestrator import (
    _guard_no_silent_decision_omission,
    _detect_operation_mode,
)
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.canonical_state import ExecutionPlan, ExecutionStep
from src.eureka.universe.problem_model import StructuredProblem, TaskNetwork


def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _sp() -> StructuredProblem:
    sp = StructuredProblem(
        questions=[], entities=[], variables=[], relationships=[], assumptions=[],
        unknowns=[], evidence_requirements=[], constraints=[], success_criteria=[],
    )
    sp.task_network = TaskNetwork(tasks=[])
    return sp


def _step(sid, em, cap, target, prod=False, deps=None):
    return ExecutionStep(
        step_id=sid, capability_id=cap, target=target, canonical_em=em, status="PENDING",
        dependencies=deps or [], expected_outputs=[], produces_result=prod,
    )


def _descriptor_publisher_plan():
    p = ExecutionPlan()
    p.steps.append(_step("d1", "EM Descriptor", "extract_relevant_information", "EM[SEMANTIC]"))
    p.steps.append(_step("pub", "EM Publisher", "generate_summary", "SUBSYSTEM", prod=True, deps=["d1"]))
    return p


# --- No silent omission, task-driven (NO forced chain) ---
def test_no_forced_chain_when_no_decision_signal():
    cr, sp = _reg(), _sp()
    p = _descriptor_publisher_plan()
    _guard_no_silent_decision_omission(p, type("P", (), {"alternatives": []})(), sp, "DECISION", cr)
    assert [s.canonical_em for s in p.steps] == ["EM Descriptor", "EM Publisher"]  # unchanged


def test_routes_prescriptor_only_when_alternatives_exist():
    cr, sp = _reg(), _sp()
    p = _descriptor_publisher_plan()
    _guard_no_silent_decision_omission(p, type("P", (), {"alternatives": ["a", "b"]})(), sp, "DECISION", cr)
    ems = [s.canonical_em for s in p.steps]
    # only the required prescription stage is routed; NO fixed chain
    assert "EM Prescriptor" in ems
    assert "EM Predictor" not in ems
    assert "EM Actioner" not in ems
    assert "EM Installer" not in ems
    # must not duplicate Publisher (already present)
    assert ems.count("EM Publisher") == 1
    # a matching CognitiveTask (owner EM Prescriptor) is routed for the runtime dispatch
    assert any(t.owner == "EM Prescriptor" for t in sp.task_network.tasks)


def test_actioner_installer_publisher_never_auto_added():
    cr, sp = _reg(), _sp()
    p = _descriptor_publisher_plan()
    _guard_no_silent_decision_omission(p, type("P", (), {"alternatives": ["x"]})(), sp, "DECISION", cr)
    ems = {s.canonical_em for s in p.steps}
    assert "EM Actioner" not in ems
    assert "EM Installer" not in ems


def test_no_duplicate_when_prescriptor_present():
    cr, sp = _reg(), _sp()
    p = _descriptor_publisher_plan()
    p.steps.append(_step("pre", "EM Prescriptor", "evaluate_alternatives", "EM[RANKING]", deps=["d1"]))
    n = len(p.steps)
    _guard_no_silent_decision_omission(p, type("P", (), {"alternatives": ["a"]})(), sp, "DECISION", cr)
    assert len(p.steps) == n  # idempotent / no duplication


def test_idempotent():
    cr, sp = _reg(), _sp()
    p = _descriptor_publisher_plan()
    prob = type("P", (), {"alternatives": ["a", "b"]})()
    _guard_no_silent_decision_omission(p, prob, sp, "DECISION", cr)
    n = len(p.steps)
    _guard_no_silent_decision_omission(p, prob, sp, "DECISION", cr)
    assert len(p.steps) == n


def test_knowledge_answer_noop():
    cr, sp = _reg(), _sp()
    p = _descriptor_publisher_plan()
    _guard_no_silent_decision_omission(p, type("P", (), {"alternatives": ["a", "b"]})(), sp, "KNOWLEDGE_ANSWER", cr)
    assert [s.canonical_em for s in p.steps] == ["EM Descriptor", "EM Publisher"]


# --- Routing sanity (preserve 67d3824) ---
def test_declarative_analysis_is_decision():
    assert _detect_operation_mode(
        "Analizar el comportamiento de ventas y detectar los principales patrones.", "REPORT") == "DECISION"
    assert _detect_operation_mode("Genera un reporte de ventas.", "REPORT") == "KNOWLEDGE_ANSWER"
    assert _detect_operation_mode("Resume el comportamiento de ventas.", "SUMMARY") == "KNOWLEDGE_ANSWER"
    assert _detect_operation_mode("¿Cuál fue el total de ventas?", "QUESTION") == "KNOWLEDGE_ANSWER"
