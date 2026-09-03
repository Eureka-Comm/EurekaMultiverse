from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class EnterpriseIntent(BaseModel):
    """
    Represents the business goal or intent requested by the Enterprise.
    This contract focuses purely on 'WHAT' is needed, without specifying 'HOW' or 'WHO'.
    """
    intent_id: str = Field(..., description="Unique identifier for this intent")
    objective: str = Field(..., description="Semantic objective, e.g., 'EVALUATE_PREDICATES'")
    domain: str = Field(..., description="The semantic domain of the intent, e.g., 'DES-001'")
    requested_outputs: List[str] = Field(default_factory=list, description="Requested knowledge types or outputs")
    evidence_requirements: List[str] = Field(default_factory=list, description="Requirements for evidence or provenance")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Execution or logical constraints")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional opaque intent metadata")
