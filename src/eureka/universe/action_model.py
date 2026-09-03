from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ActionStep(BaseModel):
    action_id: str
    description: str
    owner: str
    prerequisites: List[str] = Field(default_factory=list)
    inputs: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # Action IDs that this step depends on
    constraints: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    # Gap 3 — Actioner contract (additive & truthful): carried from the engine when actually supplied.
    code: Optional[str] = None
    api_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    validation_requirements: List[str] = Field(default_factory=list)

class ActionPlanProposal(BaseModel):
    selected_alternative_id: Optional[str] = None
    human_decision_id: Optional[str] = None
    rationale: str = ""
    execution_conditions: List[str] = Field(default_factory=list)
    validity_conditions: List[str] = Field(default_factory=list)
    uncertainty: List[str] = Field(default_factory=list)
    prescription_ref: str
    proposed_actions: List[ActionStep] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    # Gap 3 — carried from the engine when actually supplied (never fabricated).
    sequence: List[str] = Field(default_factory=list)
    code: List[Dict[str, Any]] = Field(default_factory=list)
    api_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    validation_requirements: List[str] = Field(default_factory=list)
    confirmation_required: bool = True

class ValidatedActionPlan(BaseModel):
    selected_alternative_id: Optional[str] = None
    human_decision_id: Optional[str] = None
    rationale: str = ""
    execution_conditions: List[str] = Field(default_factory=list)
    validity_conditions: List[str] = Field(default_factory=list)
    uncertainty: List[str] = Field(default_factory=list)
    plan_id: str
    prescription_ref: str
    actions: List[ActionStep] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    authority: str
    provenance: List[str] = Field(default_factory=list)
    validation_status: str
    version: int = 1
    # Gap 3 — Actioner contract (additive & truthful).
    sequence: List[str] = Field(default_factory=list)
    code: List[Dict[str, Any]] = Field(default_factory=list)
    api_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    validation_requirements: List[str] = Field(default_factory=list)
    confirmation_required: bool = True
