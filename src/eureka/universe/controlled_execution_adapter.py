from typing import List, Dict, Any, Optional
import uuid
import datetime

from .installation_model import ExecutionRequest, ExecutionAuthorization, ExecutionObservation, ExecutionEvidence
from .action_model import ValidatedActionPlan

class ControlledExecutionAdapter:
    """
    TEST_DOUBLE for execution. 
    It cannot declare success directly; it only produces ExecutionObservations.
    The Installer decides what to do with these observations.
    """
    
    def __init__(self, authorized_resources: List[str] = None, fail_actions: List[str] = None):
        self.authorized_resources = authorized_resources or []
        self.fail_actions = fail_actions or [] # Actions to simulate failure
        self.history: List[ExecutionObservation] = []

    def verify_authorization(self, request: ExecutionRequest, plan: ValidatedActionPlan, expected_level: int = 1) -> ExecutionAuthorization:
        # Simulated verification
        if request.target_execution_level > expected_level:
            # We don't throw here, we just return an auth with a lower level, 
            # and Installer must check if it matches target.
            pass
            
        auth_level = expected_level
        
        auth = ExecutionAuthorization(
            authorization_id=f"AUTH-{uuid.uuid4().hex[:6]}",
            request_ref=request.request_id,
            authorized_execution_level=auth_level,
            authorized_by="SystemTest",
            authorized_actions=[a.action_id for a in plan.actions]
        )
        return auth

    def execute_action(self, action_id: str, plan: ValidatedActionPlan, auth: ExecutionAuthorization) -> ExecutionEvidence:
        observations = []
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Check authorization
        if action_id not in auth.authorized_actions:
            observations.append(ExecutionObservation(
                action_id=action_id,
                timestamp=now,
                observation_type="SECURITY_ERROR",
                content="Action not authorized",
                is_error=True
            ))
            return ExecutionEvidence(evidence_id=f"EV-{uuid.uuid4().hex[:6]}", action_id=action_id, observations=observations)

        if action_id in self.fail_actions:
            observations.append(ExecutionObservation(
                action_id=action_id,
                timestamp=now,
                observation_type="EXECUTION_ERROR",
                content="Simulated failure occurred",
                is_error=True
            ))
        else:
            observations.append(ExecutionObservation(
                action_id=action_id,
                timestamp=now,
                observation_type="STDOUT",
                content="Execution step completed successfully in simulation",
                is_error=False
            ))
            
        return ExecutionEvidence(evidence_id=f"EV-{uuid.uuid4().hex[:6]}", action_id=action_id, observations=observations)
