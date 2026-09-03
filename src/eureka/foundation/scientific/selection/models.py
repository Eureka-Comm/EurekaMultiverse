from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class AuthoritySourceType(str, Enum):
    DOCUMENT = "DOCUMENT"
    HUMAN = "HUMAN"
    LLM = "LLM"
    MATHEMATICAL = "MATHEMATICAL"
    NORMATIVE = "NORMATIVE"
    EUREKA_ARCHITECTURAL = "EUREKA_ARCHITECTURAL"
    UNVERIFIED = "UNVERIFIED"

class ConfirmationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    UNVERIFIED = "UNVERIFIED"

class DecisionRuleSpec(BaseModel):
    rule_id: str
    input_type: str
    comparison_operator: str
    selection_operator: str
    constraints: List[str] = Field(default_factory=list)
    authority_source: str
    authority_type: AuthoritySourceType
    confirmation_status: ConfirmationStatus
    provenance: str

class SelectionAuthority(BaseModel):
    authority_type: AuthoritySourceType
    source: str
    rule_id: Optional[str] = None
    rule_expression: Optional[str] = None
    scope: str
    confirmation_status: ConfirmationStatus
    provenance: str
    validation_status: str

    def is_authorized(self) -> bool:
        if self.authority_type == AuthoritySourceType.UNVERIFIED:
            return False
        if self.confirmation_status != ConfirmationStatus.CONFIRMED:
            return False
        return True
