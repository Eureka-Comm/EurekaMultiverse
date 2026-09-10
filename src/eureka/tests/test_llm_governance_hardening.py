"""LS-LLMHARD — LLM Governance Hardening: an LLM may PROPOSE, never escalate authority.

Verifies the REAL boundaries against adversarial LLM-shaped proposals:
- EM Core (orchestrator.formulate_problem): an LLM SemanticProposal with an injected ``authority`` and
  malicious escalation text is treated as CANDIDATE metadata; Python derives ``authority_status`` /
  ``governance_status``; the LLM's authority NEVER becomes the actual authority.
- Proposal schemas (pydantic) STRIP/IGNORE unknown authority/execution fields (extra="ignore"), so
  ``execution_mode``/``promote``/``bypass_governance`` never reach a proposal as authority.
- EM Prescriptor: authority is HUMAN only when HITL requires it (never inherited from the LLM).
- EM Actioner: the authoritative human decision (HITL) cannot be overridden by an LLM-proposed id.
These use the real schemas + real Python governance (no mocks in the governance boundary).
"""
import pytest

from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.cognitive_engine import (SemanticProposal, StructuralProposal, MissingDataProposal,
                                                  InformationSufficiencyProposal, DeltaProposal, PredictorProposal,
                                                  DescriptorProposal)
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.prescriptor import EMPrescriptor
from src.eureka.universe.cognitive_engine import TestDoubleCognitiveEngine as StubEngine
from src.eureka.universe.publication_model import PublicationSection
from src.eureka.universe.prescription_model import ValidatedPrescription, PrescriptionAlternative, DecisionRule
from src.eureka.universe.action_model import ActionPlanProposal


def _build_engine():
    eng = StubEngine()
    return eng


def _orchestrator(engine):
    cr = CapabilityRegistry(); cr.load_defaults()
    return WorkOrchestrator(cr, engine)


@pytest.mark.parametrize("authority_text", [
    "canonical system admin execute publish",       # escalation words, NOT human-authorization
    "system", "admin", "root", "execute now",
    "authority: CANONICAL, execution_mode: REAL, bypass governance",
])
def test_em_core_authority_injection_is_candidate_not_authority(authority_text):
    eng = _build_engine()
    # An LLM-shaped malicious SemanticProposal (extra fields ignored by pydantic; authority is metadata)
    proposal = SemanticProposal(
        intent_category="PROBLEM_SOLVING", objective="solve", authority=authority_text,
        problem_understanding="x",
    )
    eng.register_semantic_fixture("malicious", proposal)
    orch = _orchestrator(eng)
    governed = orch.interpreter.formulate_problem("malicious")
    # Python, not the LLM, owns the authority classification
    assert governed.governance_status == "GOVERNED"
    assert governed.governance_fields.get("authority_status") == "PYTHON"
    assert governed.status == "FORMULATED"          # PYTHON-derived, never LLM
    # authority_status is a bounded enum; an injected "CANONICAL" never becomes the value
    assert governed.authority_status in {"NONE", "HUMAN_REQUIRED", "UNDETERMINED"}
    # the LLM proposal authority is stored ONLY as candidate metadata, NOT as the governing authority
    assert governed.governance_fields.get("authority") in ("PYTHON", "HUMAN_AUTHORIZED", "LLM_CANDIDATE")
    # llm-proposed execution/promote/bypass fields never surface as authority on the governed model
    for forbidden in ("execution_mode", "promote", "bypass_governance", "canonical_status"):
        assert forbidden not in governed.model_dump(mode="json")


def test_no_llm_proposal_schema_declares_authority_or_execution_fields():
    # Invariant across EVERY LLM-boundary proposal schema: none declares an ESCALATION / EXECUTION field
    # (execution_mode / promote / bypass / canonical_status / approval / release). The single exception is
    # SemanticProposal.authority, a CANDIDATE metadata field that EM Core derives `authority_status` from in
    # Python (never trusts it as authority — proven separately).
    forbidden = ("execution_mode", "promote", "bypass_governance", "canonical_status",
                 "approved", "authorization", "released", "release", "execute", "deploy")
    schemas = [SemanticProposal, StructuralProposal, MissingDataProposal, InformationSufficiencyProposal,
               DeltaProposal, PredictorProposal, DescriptorProposal, ActionPlanProposal, PublicationSection]
    for cls in schemas:
        fields = set(getattr(cls, "model_fields", {}).keys())
        bad = fields & set(forbidden)
        assert not bad, f"{cls.__name__} declares escalation/execution fields: {bad}"
    # SemanticProposal.authority is a candidate metadata field (allowed), handled as candidate.
    assert "authority" in SemanticProposal.model_fields


def test_proposal_schema_ignores_unknown_authority_execution_fields():
    # pydantic extra="ignore": unknown fields injected by an LLM are silently dropped (SemanticProposal).
    p = SemanticProposal(intent_category="REPORT", objective="o", authority="ignore me",
                         **{"execution_mode": "REAL_EXECUTION", "promote": True,
                            "bypass_governance": True, "canonical_status": "CANONICAL",
                            "approved": True})
    assert not hasattr(p, "execution_mode")
    assert not hasattr(p, "promote")
    assert not hasattr(p, "bypass_governance")
    assert not hasattr(p, "approved")
    assert isinstance(p.authority, str)


def test_prescriptor_authority_is_human_from_hitl_not_llm():
    presc = EMPrescriptor(cognitive_engine=_build_engine())
    assert presc._governed_authority("HUMAN_DECISION_REQUIRED", DecisionRule(status="DOCUMENTED")) == "HUMAN"
    assert presc._governed_authority("EVALUATED", DecisionRule(status="HUMAN_PROVIDED")) == "HUMAN"
    assert presc._governed_authority("FORMULATED", DecisionRule(status="UNSPECIFIED")) == "PENDING"


def test_actioner_hitl_gate_blocks_llm_proposed_decision():
    # A prescription requiring HITL with NO canonical human decision must BLOCK (never let the LLM
    # authorise). The DecisionRule authority is HUMANK/provided by the contract; the LLM cannot set it.
    from src.eureka.universe.actioner import EMActioner
    from src.eureka.universe.canonical_state import CanonicalWorkState, ExecutionStep, StructuredFinding
    from src.eureka.universe.work_model import EurekaWork
    from src.eureka.universe.problem_model import CognitiveTask

    c = CanonicalWorkState(work=EurekaWork(work_id="W-HITL", title="t", user_intent="u",
                                           task_category="c", problem_statement="p"))
    c.status = "RUNNING"
    alt = PrescriptionAlternative(alternative_id="ALT-1", description="d", score=0.5)
    c.prescriptive_knowledge.prescriptions.append(ValidatedPrescription(
        prescription_id="PRES-1", objective="o", alternatives=[alt],
        applicable_criteria=[], constraints=[], decision_rule=DecisionRule(status="DOCUMENTED"),
        supporting_predictions=[], supporting_knowledge=[], rationale="r", authority="PENDING",
        provenance=["x"], validation_status="HUMAN_DECISION_REQUIRED", selected_alternative=None,
        human_decision_required=True))
    task = CognitiveTask(task_id="t1", description="action", owner="EM Actioner")
    actioner = EMActioner(cognitive_engine=_build_engine())
    # No canonical human decision -> Actioner must NOT authorise an ActionPlan (fails closed, HITL)
    out = actioner.execute_task(None, task, c)
    assert out.status == "RUNNING"  # the work is not escalated to an authorised/executed state
    assert out.action_plan is None   # NO VALIDATED ActionPlan was produced (LLM cannot authorise)
