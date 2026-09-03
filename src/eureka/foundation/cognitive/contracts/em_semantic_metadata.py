from pydantic import BaseModel, Field
from typing import List, Dict, Any

class EMSemanticMetadata(BaseModel):
    """
    Metadata exposing what an EM does, allowing the Cognitive Planner to discover and select it
    without executing it or inspecting its internals.
    """
    supported_objectives: List[str] = Field(default_factory=list, description="Objectives this EM can fulfill")
    semantic_domain: str = Field(..., description="The semantic domain this EM operates in")
    produced_knowledge_types: List[str] = Field(default_factory=list, description="Categories of knowledge produced")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Operational or domain constraints")
    version: str = Field("1.0", description="EM Version")
