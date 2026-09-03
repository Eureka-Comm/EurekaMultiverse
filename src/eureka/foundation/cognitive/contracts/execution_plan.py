from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from eureka_cognitive_sdk.core.identifiers.module_id import ModuleId
from .intent import EnterpriseIntent
from .capability_requirement import CapabilityRequirement

class ExecutionPlan(BaseModel):
    """
    Represents an actionable plan mapped from an EnterpriseIntent.
    Contains everything necessary for the GenericEMRunner to safely execute.
    """
    intent: EnterpriseIntent = Field(..., description="The original enterprise intent")
    selected_em_id: str = Field(..., description="The ID of the EM selected to fulfill this intent")
    em_version: str = Field(..., description="Version of the selected EM")
    required_capabilities: List[CapabilityRequirement] = Field(default_factory=list, description="Capabilities that must be resolved")
    validation_status: str = Field("PENDING", description="Validation status of this plan")
    rationale: str = Field(..., description="Human and machine readable rationale for this selection")
    provenance_requirements: List[str] = Field(default_factory=list, description="Required provenance steps")
    planner_id: str = Field(..., description="ID of the planner module that created this plan")
