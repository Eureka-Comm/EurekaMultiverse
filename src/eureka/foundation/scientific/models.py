from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

class AuthorityType(str, Enum):
    HUMAN = "HUMAN"
    LLM = "LLM"
    DOCUMENT = "DOCUMENT"
    DERIVED = "DERIVED"
    UNVERIFIED = "UNVERIFIED"

class SemanticAuthorityType(str, Enum):
    HUMAN = "HUMAN"
    LLM = "LLM"
    DOCUMENT = "DOCUMENT"
    DERIVED = "DERIVED"
    UNVERIFIED = "UNVERIFIED"

class ConfirmationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    UNVERIFIED = "UNVERIFIED"

from src.eureka.foundation.scientific.selection.models import SelectionAuthority, AuthoritySourceType, ConfirmationStatus

class ObjectivePredicate(BaseModel):
    """
    Mathematical expression representation.
    FORMULA vs EXECUTABLE EVALUATOR separation.
    """
    predicate_id: str
    expression: str
    variables: List[str]
    operators: List[str]
    source_authority: str
    provenance: str
    evaluation_semantics: str
    # Executable evaluator kept separate but callable when authorized
    evaluator: Optional[Callable[[Dict[str, float]], float]] = Field(default=None, exclude=True)

class ObjectivePredicateSpec(BaseModel):
    predicate_id: str
    variables: List[str]
    goals: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    priority_structure: Dict[str, str] = Field(default_factory=dict)
    candidate_mappings: Dict[str, str] = Field(default_factory=dict)
    logical_structure: str
    operators: List[str]
    authority_source: str
    semantic_authority: SemanticAuthorityType = SemanticAuthorityType.UNVERIFIED
    confirmation_status: ConfirmationStatus = ConfirmationStatus.UNVERIFIED
    provenance: str
    validation_status: str = "UNVERIFIED"

class Alternative(BaseModel):
    alternative_id: str
    data: Dict[str, float]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvaluationResult(BaseModel):
    alternative_id: str
    predicate_id: str
    truth_value: float
    utility_value: Optional[float]
    utility_semantics: str
    authority_source: str
    trace_id: str
    provenance: str

class SemanticDecisionContext(BaseModel):
    goals: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    priorities: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    risk_preferences: List[str] = Field(default_factory=list)
    objective_predicate: Optional[ObjectivePredicate] = None
    alternative_set: List[Alternative] = Field(default_factory=list)
    authority_type: AuthorityType = AuthorityType.UNVERIFIED
    authority_source: str = ""
    selection_authority: Optional[SelectionAuthority] = None
    prescription_authority: Optional[str] = None
