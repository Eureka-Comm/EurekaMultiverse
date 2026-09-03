# -*- coding: utf-8 -*-
"""LS90 — tests for the governed OPEN-RESEARCH ("what remains open") projection.

`build_open_research_state` is a deterministic, read-only, Python-derived view of
the leading edge of an OPEN cognitive operation (an open research question that has
NOT yet reached a decision). It must:
  · aggregate REAL canonical fields (unknowns / uncertainty / limitations /
    contradictions / not-evaluated / insufficient information / data-not-available /
    pending human decision) WITHOUT inventing a decision, ranking, or preference;
  · never turn LLM output into authority;
  · never re-route execution (it is a derived view, like build_core_analysis / story).
"""

import pytest

from src.eureka.universe.canonical_state import (
    CanonicalWorkState,
    HumanDecision,
    build_open_research_state,
)
from src.eureka.universe.problem_model import ProblemModel
from src.eureka.universe.work_model import EurekaWork


def _state(problem=None, **kw):
    return CanonicalWorkState(
        work=EurekaWork(work_id="W", title="t", user_intent="q", task_category="DYNAMIC", problem_statement="q"),
        problem=problem or ProblemModel(intent="q", objective="Obj"),
        **kw,
    )


def test_open_operation_is_open_with_insufficient_information():
    c = _state(
        problem=ProblemModel(
            intent="q", objective="Conocer el estado de la técnica sobre X",
            unknowns=["No hay datos cuantitativos sobre X"], questions=["¿Qué evidencia existe?"],
        ),
        knowledge_state="INCOMPLETE",
    )
    # predictive knowledge status defaults to UNAVAILABLE (no prediction produced)
    c.predictive_knowledge.status = "UNAVAILABLE"
    c.result = type("R", (), {"status": "PARTIAL"})()  # no validated analysis

    o = build_open_research_state(c)
    assert o is not None
    assert o.operation_kind == "OPEN_RESEARCH"
    assert o.is_open is True
    assert o.decision_reached is False
    assert o.decision_pending is True
    assert o.status == "OPEN_INSUFFICIENT_INFORMATION"
    kinds = [i.kind for i in o.items]
    assert "UNRESOLVED_QUESTION" in kinds
    assert "PENDING_HUMAN_DECISION" in kinds
    assert "DATA_NOT_AVAILABLE" in kinds          # predictive_knowledge.status == UNAVAILABLE
    assert "INSUFFICIENT_INFORMATION" in kinds    # knowledge_state INCOMPLETE + PARTIAL result
    for i in o.items:
        assert i.kind in {
            "UNRESOLVED_QUESTION", "INSUFFICIENT_INFORMATION", "INSUFFICIENT_DATA",
            "MISSING_EVIDENCE", "UNCERTAINTY", "LIMITATION", "CONTRADICTION",
            "PENDING_HUMAN_DECISION", "PENDING_HUMAN_INPUT", "NOT_EVALUATED", "DATA_NOT_AVAILABLE",
        }
        assert i.source_ref  # provenance-ref present


def test_decision_reached_operation_is_closed():
    c = _state()
    c.human_decision = HumanDecision(
        decision_id="DEC-1", work_id="W", decision_type="SELECT_ALTERNATIVE",
        selected_alternative_id="ALT-01", timestamp="now",
    )
    c.knowledge_state = "COMPLETE"
    o = build_open_research_state(c)
    assert o.operation_kind == "DECISION"
    assert o.is_open is False
    assert o.decision_reached is True
    assert o.decision_pending is False
    assert o.status == "CLOSED"


def test_predictor_honest_refusal_is_surfaced_not_invented():
    """A prediction that was never evaluated is surfaced as NOT_EVALUATED, never as a number."""
    c = _state()
    c.predictive_knowledge.status = "IN_PROGRESS"
    c.predictive_knowledge.predictions = [type("P", (), {
        "prediction_id": "PRED-1", "predicted_value": None, "mse": None,
        "validation_status": "NOT_EVALUATED",
        "uncertainty": type("U", (), {"status": "NOT_AVAILABLE"})(),
        "evidence_refs": [],
    })()]
    o = build_open_research_state(c)
    kinds = [i.kind for i in o.items]
    assert "NOT_EVALUATED" in kinds
    assert "INSUFFICIENT_INFORMATION" in kinds  # uncertainty NOT_AVAILABLE
    # no numeric value is ever asserted
    assert not any(i.label.endswith("= 4.2") for i in o.items)


def test_none_state_returns_none():
    assert build_open_research_state(None) is None


def test_provenance_is_python_derived_not_llm():
    o = build_open_research_state(_state())
    assert any("Python-derived" in p for p in o.provenance)
    # The provenance declares governance, but must NOT claim the LLM produced the
    # open-state (LLM = candidate only). We assert the absence of LLM-as-authority.
    assert not any(("LLM-generated" in p) or ("from the LLM" in p) for p in o.provenance)
