from pydantic import BaseModel, Field
from typing import Optional

class CapabilityRequirement(BaseModel):
    requirement_id: str = Field(..., description="Unique ID for this requirement within the EM")
    semantic_role: str = Field(..., description="The semantic purpose of this capability")
    capability_type: str = Field(..., description="The required formula or capability type identifier (e.g. F007)")
    version: Optional[str] = Field(None, description="Optional version pin")
    constraints: Optional[dict] = Field(default_factory=dict, description="Execution constraints or hints")
