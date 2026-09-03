from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class PrescriptionCriterion(BaseModel):
    criterion_id: str
    description: str
    target: str
    direction: Literal["MINIMIZE", "MAXIMIZE", "MATCH"]
    threshold: Optional[float] = None
    weight: Optional[float] = None
    authority: str
    provenance: List[str] = Field(default_factory=list)

class ExpectedOutcome(BaseModel):
    alternative_id: str
    outcome: str
    value: Optional[str] = None

class Tradeoff(BaseModel):
    dimension: str
    positive: str = ""
    negative: str = ""

class Risk(BaseModel):
    description: str
    severity: Optional[str] = None
    probability: Optional[float] = None
    mitigation: str = ""

class PrescriptionAlternative(BaseModel):
    alternative_id: str
    description: str
    expected_effects: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    # Gap 2: a derived (real, from acfl.normalized_scores) per-alternative scalar score.
    score: Optional[float] = None

class DecisionRule(BaseModel):
    status: Literal["DOCUMENTED", "HUMAN_PROVIDED", "UNSPECIFIED"]
    rule_type: Optional[str] = None
    authority: Optional[str] = None
    description: Optional[str] = None

class PrescriptionProposal(BaseModel):
    prescription_id: str
    objective: str
    alternatives: List[PrescriptionAlternative] = Field(default_factory=list)
    criteria: List[PrescriptionCriterion] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    decision_rule: Optional[DecisionRule] = None
    rationale: str
    evidence_refs: List[str] = Field(default_factory=list)
    prediction_refs: List[str] = Field(default_factory=list)
    # Gap 2 (schedule parity): the proposal MAY carry these from the engine (real analysis).
    expected_outcomes: List[ExpectedOutcome] = Field(default_factory=list)
    tradeoffs: List[Tradeoff] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)

class ValidatedPrescription(BaseModel):
    prescription_id: str
    objective: str
    alternatives: List[PrescriptionAlternative]
    applicable_criteria: List[PrescriptionCriterion]
    constraints: List[str]
    decision_rule: DecisionRule
    selected_alternative: Optional[PrescriptionAlternative] = None
    supporting_predictions: List[str]
    supporting_knowledge: List[str]
    rationale: str
    authority: str
    provenance: List[str]
    validation_status: Literal["FORMULATED", "EVALUATED", "SELECTED", "HUMAN_DECISION_REQUIRED", "INVALID"]
    version: int = 1
    # Gap 2 (PrescriptiveResult parity) — additive, truthful. Derived from real data where possible;
    # carried from the engine proposal when provided.
    expected_outcomes: List[ExpectedOutcome] = Field(default_factory=list)
    tradeoffs: List[Tradeoff] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    validation_checks: List[str] = Field(default_factory=list)
    human_decision_required: bool = False

class PrescriptiveKnowledgeState(BaseModel):
    status: Literal["INCOMPLETE", "FORMULATING", "FROZEN"] = "INCOMPLETE"
    prescriptions: List[ValidatedPrescription] = Field(default_factory=list)
    version: int = 1
