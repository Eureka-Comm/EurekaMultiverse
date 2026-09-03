from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from .action_model import ValidatedActionPlan

class ExecutionRequest(BaseModel):
    request_id: str
    action_plan_ref: str
    target_execution_level: int
    requested_by: str

class ExecutionAuthorization(BaseModel):
    authorization_id: str
    request_ref: str
    authorized_execution_level: int
    authorized_by: str
    authorized_actions: List[str] = Field(default_factory=list)

class ExecutionObservation(BaseModel):
    action_id: str
    timestamp: str
    observation_type: str # e.g. "STDOUT", "EXIT_CODE", "API_RESPONSE"
    content: str
    is_error: bool = False

class ExecutionEvidence(BaseModel):
    evidence_id: str
    action_id: str
    observations: List[ExecutionObservation] = Field(default_factory=list)

class ExecutionResult(BaseModel):
    result_id: str
    request_ref: str
    status: str # SUCCEEDED, PARTIALLY_SUCCEEDED, FAILED, ROLLED_BACK, NOT_VERIFIED, FAIL_CLOSED, WAITING_FOR_HUMAN_INPUT, ACTION_PLAN_INTEGRITY_FAILURE
    evidence_refs: List[str] = Field(default_factory=list)
    failed_actions: List[str] = Field(default_factory=list)
    successful_actions: List[str] = Field(default_factory=list)
    missing_authority_gap: Optional[str] = None

class ExecutionState(BaseModel):
    state_id: str
    action_plan_ref: str
    request: Optional[ExecutionRequest] = None
    authorization: Optional[ExecutionAuthorization] = None
    evidence: List[ExecutionEvidence] = Field(default_factory=list)
    result: Optional[ExecutionResult] = None
    status: str = "PENDING" # PENDING, AUTHORIZED, RUNNING, COMPLETED, BLOCKED

class InstallationState(BaseModel):
    # Distinct from execution. Installer handles this if it's a persistent system.
    installation_id: str
    status: str
    components: Dict[str, str] = Field(default_factory=dict)
