from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any

class AgentDefinition(BaseModel):
    """Definition of a Cognitive Provider agent.

    Contains only metadata and configuration; no authority fields.
    """
    agent_id: str = Field(..., description="Unique identifier for the agent")
    version: str = Field(..., description="Version string of the agent definition")
    system_prompt: str = Field(..., description="System prompt used by the LLM (non‑authoritative)")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema describing expected input payload")
    output_schema: Dict[str, Any] = Field(..., description="JSON schema describing expected output proposal")
    capabilities: List[str] = Field(..., description="List of capabilities the agent may propose")
    forbidden_operations: List[str] = Field(..., description="Explicit list of prohibited operations")
    knowledge_sources: List[str] = Field(..., description="Identifiers of knowledge sources the agent can reference")
    provider_policy: Dict[str, Any] = Field(..., description="Configuration policy for the provider (e.g., timeout, allowed models)")

    model_config = ConfigDict(extra="forbid")
