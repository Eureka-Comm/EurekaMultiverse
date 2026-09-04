"""Canonical DECISION execution-chain authority (orchestrator._ensure_decision_chain).

For a DECISION operation, Python must guarantee the canonical decision execution chain is
structurally present in the plan, even if the LLM's CognitiveTask proposal omitted some EMs.
Developer note: EM Core / EM Structurer are ORCHESTRATION-LEVEL (always run by `orchestrate` ->
formulate_problem / build_network, shown COMPLETED in the rail). The runtime represents the
executable chain as Descriptor -> Publisher, so the guarantee targets those plan-level EMs.
"""
import pytest

from src.eureka.universe.orchestrator import (
    _ensure_decision_chain,
    _detect_operation_mode,
    WorkOrchestrator,
)
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.canonical_state import ExecutionPlan, ExecutionStep
from src.eureka.universe.problem_model import StructuredProblem, TaskNetwork
from src.eureka.universe.cognitive_engine import TestDoubleCognitiveEngine

PLAN_EM_CHAIN = ("EM Descriptor", "EM Predictor", "EM Prescriptor", "EM Actioner", "EM Installer", "EM Publisher")


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


# TEST 1 — DECISION with an incomplete LLM proposal (only Descriptor + Publisher) is completed.
def test_decision_chain_adds_missing_ems():
    cr, sp = _reg(), _sp()
    plan = ExecutionPlan()
    plan.steps.append(_step("t_desc", "EM Descriptor", "extract_relevant_information", "EM[SEMANTIC]"))
    plan.steps.append(_step("t_pub", "EM Publisher", "generate_summary", "SUBSYSTEM", prod=True, deps=["t_desc"]))

    _ensure_decision_chain(plan, sp, "DECISION", cr)

    ems = {s.canonical_em for s in plan.steps}
    assert set(PLAN_EM_CHAIN) <= ems
    # Prescriptor/Actioner/Installer need a matching CognitiveTask (runtime looks up by step_id/owner)
    owners = {t.owner for t in sp.task_network.tasks}
    assert {"EM Prescriptor", "EM Actioner", "EM Installer"} <= owners


# TEST 2 — DECISION already has Predictor: Python adds Prescriptor/Actioner/Installer WITHOUT duplicating Predictor.
def test_decision_chain_does_not_duplicate_predictor():
    cr, sp = _reg(), _sp()
    plan = ExecutionPlan()
    plan.steps.append(_step("d", "EM Descriptor", "extract_relevant_information", "EM[SEMANTIC]"))
    plan.steps.append(_step("p", "EM Predictor", "analyze_dataset", "EM[SCIENTIFIC]"))

    _ensure_decision_chain(plan, sp, "DECISION", cr)

    assert sum(1 for s in plan.steps if s.canonical_em == "EM Predictor") == 1
    assert {"EM Prescriptor", "EM Actioner", "EM Installer"} <= {s.canonical_em for s in plan.steps}


# TEST 3 — DECISION already complete: no duplicates are introduced.
def test_decision_chain_complete_no_duplicates():
    cr, sp = _reg(), _sp()
    plan = ExecutionPlan()
    specs = [
        ("EM Descriptor", "extract_relevant_information", "EM[SEMANTIC]", False),
        ("EM Predictor", "analyze_dataset", "EM[SCIENTIFIC]", False),
        ("EM Prescriptor", "evaluate_alternatives", "EM[RANKING]", False),
        ("EM Actioner", "execute_action", "EM[ACTIONER]", False),
        ("EM Installer", "install_action", "EM[INSTALLER]", False),
        ("EM Publisher", "generate_summary", "SUBSYSTEM", True),
    ]
    for em, cap, target, prod in specs:
        plan.steps.append(_step(em.lower().replace(" ", "_"), em, cap, target, prod))
    n = len(plan.steps)

    _ensure_decision_chain(plan, sp, "DECISION", cr)

    assert len(plan.steps) == n


# TEST 4 — dependencies follow the canonical EM rank (no backward edges) after normalization.
def test_decision_chain_dependencies_rank_order():
    cr, sp = _reg(), _sp()
    plan = ExecutionPlan()
    plan.steps.append(_step("t_desc", "EM Descriptor", "extract_relevant_information", "EM[SEMANTIC]"))
    plan.steps.append(_step("t_pub", "EM Publisher", "generate_summary", "SUBSYSTEM", prod=True, deps=["t_desc"]))
    _ensure_decision_chain(plan, sp, "DECISION", cr)

    wo = WorkOrchestrator(cr, TestDoubleCognitiveEngine())
    wo._normalize_em_pipeline_order(plan)

    order = {n: i for i, n in enumerate(("EM Core", "EM Structurer", "EM Descriptor", "EM Predictor",
                                         "EM Prescriptor", "EM Actioner", "EM Installer", "EM Publisher"))}
    rank = {s.step_id: order.get(s.canonical_em, 99) for s in plan.steps}
    for s in plan.steps:
        for d in (s.dependencies or []):
            # a step may only depend on a same-or-strictly-lower-rank EM (no back-edges -> acyclic)
            assert rank.get(d, 99) <= rank.get(s.step_id, 99)
    # Prescriptor must depend on the Descriptor step (or a lower-rank step), never on Publisher.
    presc = next(s for s in plan.steps if s.canonical_em == "EM Prescriptor")
    assert "t_pub" not in (presc.dependencies or [])


# TEST 5 — idempotent: applying twice yields the same logical plan.
def test_decision_chain_idempotent():
    cr, sp = _reg(), _sp()
    plan = ExecutionPlan()
    plan.steps.append(_step("d", "EM Descriptor", "extract_relevant_information", "EM[SEMANTIC]"))
    _ensure_decision_chain(plan, sp, "DECISION", cr)
    ems = [s.canonical_em for s in plan.steps]
    _ensure_decision_chain(plan, sp, "DECISION", cr)
    assert [s.canonical_em for s in plan.steps] == ems


# TEST 6 — KNOWLEDGE_ANSWER must NOT receive the decision chain.
def test_decision_chain_knowledge_noop():
    cr, sp = _reg(), _sp()
    plan = ExecutionPlan()
    plan.steps.append(_step("d", "EM Descriptor", "extract_relevant_information", "EM[SEMANTIC]"))
    _ensure_decision_chain(plan, sp, "KNOWLEDGE_ANSWER", cr)
    assert [s.canonical_em for s in plan.steps] == ["EM Descriptor"]


# TEST 7 — declarative analysis routing regression (previous fix preserved).
def test_declarative_analysis_routing():
    assert _detect_operation_mode(
        "Analizar el comportamiento de ventas y detectar los principales patrones.", "REPORT") == "DECISION"
    assert _detect_operation_mode("Genera un reporte de ventas.", "REPORT") == "KNOWLEDGE_ANSWER"
    assert _detect_operation_mode("Resume el comportamiento de ventas.", "SUMMARY") == "KNOWLEDGE_ANSWER"
