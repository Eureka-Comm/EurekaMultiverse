from typing import List, Dict
from eureka_cognitive_sdk.ekp.package import EnterpriseKnowledgePackage
from eureka_cognitive_sdk.ekp.artifacts.knowledge import Knowledge, KnowledgeContext, KnowledgeConstraints, KnowledgeAssumptions
from eureka.foundation.cognitive.contracts.em_contract import EMExecutionContract
from eureka.foundation.cognitive.contracts.capability_requirement import CapabilityRequirement
from eureka.foundation.scientific.runtime.assembly import ExecutableRuntimeCapability
from eureka_cognitive_sdk.core.identifiers.trace_id import TraceId
from eureka_cognitive_sdk.core.identifiers.knowledge_id import KnowledgeId
from eureka_cognitive_sdk.core.value_objects.enumerations import KnowledgeCategory
from eureka_cognitive_sdk.core.value_objects.primitives import ConfidenceScore
from eureka_cognitive_sdk.core.identifiers.document_id import DocumentId
from eureka_cognitive_sdk.core.identifiers.module_id import ModuleId
from eureka_cognitive_sdk.ekp.provenance import Provenance
import uuid
from datetime import datetime, timezone

class EMActionerEngine(EMExecutionContract):
    """EMActionerEngine implements the minimal integration boundary for MVP.
    
    This establishes the PARTIAL structural materialization of the Actioner.
    It reads the prescriptive knowledge, validates its mechanical availability,
    and correctly flags downstream execution as BLOCKED if the cognitive decision
    is NOT_MATERIALIZED.
    """

    @property
    def em_id(self) -> str:
        return "emactioner"

    def get_capability_requirements(self) -> List[CapabilityRequirement]:
        return []

    def execute(
        self,
        ekp: EnterpriseKnowledgePackage,
        capabilities: Dict[str, ExecutableRuntimeCapability],
        trace_id: TraceId,
    ) -> List[Knowledge]:
        from eureka_cognitive_sdk.core.value_objects.enumerations import KnowledgeState
        
        action_plan_status = "NOT_MATERIALIZED"
        execution_status = "NOT_MATERIALIZED"
        code_gen_status = "NOT_MATERIALIZED"
        proposition_str = ""

        # ACTIONER GATE: Structural enforcement of governance boundaries
        if ekp.metadata.lifecycle_state != KnowledgeState.AUTHORIZED:
            proposition_str = f"ACTIONER BOUNDARY: BLOCKED_BY_GOVERNANCE | REASON: EKP State is {ekp.metadata.lifecycle_state.value}, expected AUTHORIZED."
            action_plan_status = "BLOCKED_BY_GOVERNANCE"
            execution_status = "BLOCKED_BY_GOVERNANCE"
        
        elif not ekp.execution_authority:
            proposition_str = "ACTIONER BOUNDARY: BLOCKED_BY_GOVERNANCE | REASON: Missing ExecutionAuthority."
            action_plan_status = "BLOCKED_BY_GOVERNANCE"
            execution_status = "BLOCKED_BY_GOVERNANCE"
            
        elif ekp.execution_authority.authority_type != "HUMAN_EXTERNAL":
            proposition_str = f"ACTIONER BOUNDARY: BLOCKED_BY_GOVERNANCE | REASON: Invalid Authority Type {ekp.execution_authority.authority_type}."
            action_plan_status = "BLOCKED_BY_GOVERNANCE"
            execution_status = "BLOCKED_BY_GOVERNANCE"
            
        elif not getattr(ekp.execution_authority, "is_explicit_confirmation", False):
            proposition_str = "ACTIONER BOUNDARY: BLOCKED_BY_GOVERNANCE | REASON: Missing explicit confirmation."
            action_plan_status = "BLOCKED_BY_GOVERNANCE"
            execution_status = "BLOCKED_BY_GOVERNANCE"
            
        else:
            # Locate the EXACT frozen artifact that was authorized
            target_id = str(ekp.execution_authority.target_knowledge_id.value)
            authorized_artifact = next((k for k in ekp.knowledge if str(k.identity.value) == target_id), None)
            
            if not authorized_artifact:
                proposition_str = f"ACTIONER BOUNDARY: BLOCKED_BY_GOVERNANCE | REASON: Target artifact {target_id} not found."
                action_plan_status = "BLOCKED_BY_GOVERNANCE"
                execution_status = "BLOCKED_BY_GOVERNANCE"
            else:
                # Mechanical Prescription Validation on the exact authorized artifact
                decision_status = authorized_artifact.structured_data.get("decision_status", "UNKNOWN")
                prescription_status = authorized_artifact.structured_data.get("prescription_status", "UNKNOWN")
                
                if decision_status == "NOT_MATERIALIZED" or prescription_status == "NOT_MATERIALIZED":
                    proposition_str = "ACTIONER BOUNDARY: BLOCKED_BY_PRESCRIPTION | REASON: Missing cognitive prescription."
                    action_plan_status = "BLOCKED_BY_PRESCRIPTION"
                    execution_status = "BLOCKED_BY_PRESCRIPTION"
                else:
                    # Actioner Gate PASS
                    proposition_str = "ACTIONER BOUNDARY: AUTHORIZED | ACTION GENERATION: REAL | EXECUTION: STRUCTURALLY_PERMITTED"
                    action_plan_status = "REAL"
                    execution_status = "STRUCTURALLY_PERMITTED"
                    
        if action_plan_status == "REAL":
            # FIX: Actioner Contract - Actually generate the ValidatedActionPlan
            from src.eureka.universe.action_model import ValidatedActionPlan, ActionStep
            action = ActionStep(
                action_id=f"ACT-{uuid.uuid4().hex[:6]}",
                description="Execute authorized capability",
                owner="EM Installer"
            )
            real_action_plan = ValidatedActionPlan(
                plan_id=f"AP-{uuid.uuid4().hex[:6]}",
                prescription_ref=str(authorized_artifact.identity.value) if 'authorized_artifact' in locals() and authorized_artifact else "N/A",
                actions=[action],
                authority="HUMAN",
                validation_status="VALIDATED"
            )
            action_plan_data = real_action_plan.model_dump()
        else:
            action_plan_data = None

        knowledge = Knowledge(
            identity=KnowledgeId(value=str(uuid.uuid4())),
            category=KnowledgeCategory.PROCESS,
            proposition=proposition_str,
            semantic_context=KnowledgeContext(process="Execution Planning"),
            supporting_evidence=[],
            constraints=KnowledgeConstraints(),
            assumptions=KnowledgeAssumptions(assumptions=[
                "Actioner governance boundary enforced.",
                "Missing cognitive decision properly blocks execution."
            ]),
            structured_data={
                "source_knowledge_id": str(authorized_artifact.identity.value) if 'authorized_artifact' in locals() and authorized_artifact else str(list(ekp.knowledge)[-1].identity.value),
                "input_integration": "REAL",
                "prescription_validation": "REAL",
                "action_plan_generation": action_plan_status,
                "action_plan": action_plan_data,
                "execution_plan": execution_status,
                "code_generation": code_gen_status,
                "runtime_execution": execution_status
            },
            confidence=ConfidenceScore(value=1.0),
            traceability=trace_id,
            provenance=Provenance(
                source_document_id=DocumentId(value="mock-doc-actioner"),
                produced_by_module=ModuleId(value=self.em_id),
                produced_at=datetime.now(timezone.utc),
                produced_from="Deterministic Structural Bypass"
            )
        )
        return [knowledge]
