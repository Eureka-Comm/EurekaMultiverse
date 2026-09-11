from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PublicationInput(BaseModel):
    # Read-only references to upstream state
    knowledge_ref: str
    predictive_knowledge_ref: Optional[str] = None
    prescriptive_knowledge_ref: Optional[str] = None
    action_plan_ref: Optional[str] = None
    execution_state_ref: Optional[str] = None

class PublicationSection(BaseModel):
    section_id: str
    section_type: str # e.g. "PROBLEM", "FINDINGS", "PREDICTIONS", "DECISIONS", "ACTIONS", "EXECUTION_RESULT", "LIMITATIONS", "UNKNOWN"
    content: str
    source_refs: List[str] = Field(default_factory=list)
    status: str
    provenance: List[str] = Field(default_factory=list)

class FrozenResult(BaseModel):
    result_id: str
    status: str = "FROZEN" # Only FROZEN or SUPERSEDED
    knowledge_version: str
    # VALIDATED knowledge only (status == "VALIDATED"). The name is the contract: UNSUPPORTED /
    # REJECTED findings must NEVER appear here.
    validated_knowledge: List[Dict[str, Any]] = Field(default_factory=list)
    # Full knowledge snapshot (ALL findings, whatever their status) kept ONLY as the content payload
    # of the freeze signature, so a frozen snapshot stays tamper-evident AND `validated_knowledge`
    # stays truthful. Legacy frozen results (no snapshot) keep the historical signature shape.
    knowledge_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    validated_predictions: List[Dict[str, Any]] = Field(default_factory=list)
    validated_prescriptions: List[Dict[str, Any]] = Field(default_factory=list)
    validated_action_plan: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    contradictions: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    freeze_signature: str

# Alias for clarity – the frozen solution contract
FrozenSolution = FrozenResult
    
class PublishedResult(BaseModel):
    published_id: str
    frozen_result_ref: Optional[str] = None  # LS48: publication is valid without a frozen asset
    sections: List[PublicationSection] = Field(default_factory=list)
    audience: str = "General"
    format: str = "DOCUMENT"
    # Gap 5 — Publisher contract (additive & truthful). Describes HOW the result was adapted to the
    # audience + references the artifact; never fabricates adapted content.
    audience_adaptation: Dict[str, Any] = Field(default_factory=dict)
    artifact: Optional[str] = None
    validation_status: str = "validated"

class PublicationState(BaseModel):
    state_id: str
    publication_input: PublicationInput
    status: str = "NOT_READY" # NOT_READY, WAITING_FOR_EVIDENCE, WAITING_FOR_HUMAN_INPUT, VALIDATED, FROZEN, PUBLISHED, BLOCKED
    publications: List[PublishedResult] = Field(default_factory=list)
