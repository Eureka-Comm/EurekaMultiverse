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

from eureka.foundation.scientific.models import SemanticDecisionContext, SelectionAuthority, Alternative
from eureka.foundation.scientific.foundation import ScientificFoundation
from eureka.foundation.scientific.builder.predicate_builder import ObjectivePredicateBuilder

class EMPrescriptorEngine(EMExecutionContract):
    """EMPrescriptorEngine implements the minimal integration contract for MVP.
    
    This establishes the PARTIAL structural materialization of the Prescriptor:
    - Infrastructure, Knowledge wrapping, Trace, and Provenance are REAL.
    - Scientific Foundation is REAL for Evaluation/Ranking.
    - Cognitive Prescription (decision and rationale) is explicitly NOT_MATERIALIZED
      unless authorized by SemanticDecisionContext.
    """

    def __init__(self, semantic_context: SemanticDecisionContext, foundation: ScientificFoundation):
        self.semantic_context = semantic_context
        self.foundation = foundation
        self.builder = ObjectivePredicateBuilder()

    @property
    def em_id(self) -> str:
        return "emprescriptor"

    def get_capability_requirements(self) -> List[CapabilityRequirement]:
        return []

    def execute(
        self,
        ekp: EnterpriseKnowledgePackage,
        capabilities: Dict[str, ExecutableRuntimeCapability],
        trace_id: TraceId,
    ) -> List[Knowledge]:
        if not ekp.knowledge or len(ekp.knowledge) == 0:
            raise RuntimeError("No knowledge found in EKP to prescribe upon.")
        
        predictive_k = list(ekp.knowledge)[-1]
        
        # Build Predicate if not present, enforcing SEMANTIC AUTHORITY BOUNDARY
        proposition_str = ""
        decision_status = ""
        evaluations_data = []
        builder_result = None

        if not self.semantic_context.objective_predicate:
            # We attempt to build it
            builder_result = self.builder.build(self.semantic_context, str(uuid.uuid4()))
            if builder_result["status"] in ["INCOMPLETE_SEMANTIC_AUTHORITY", "SEMANTIC_AUTHORITY_REQUIRED", "PARTIAL_OBJECTIVE_PREDICATE"]:
                proposition_str = f"PREDICATE_BUILDER_STOP: {builder_result['status']}"
                decision_status = builder_result["status"]
            elif builder_result["status"] == "READY_FOR_VALIDATION":
                # In a real flow, it would be converted to ObjectivePredicate after validation.
                # For this slice, we simulate stopping at readiness.
                proposition_str = "READY_FOR_EVALUATION"
                decision_status = "READY_FOR_EVALUATION"
        else:
            # STOP GATE B & C - SCIENTIFIC EVALUATION
            evaluations = []
            for alt in self.semantic_context.alternative_set:
                eval_res = self.foundation.evaluate_alternative(self.semantic_context.objective_predicate, alt)
                evaluations.append(eval_res)
            
            # STOP GATE D - RANKING
            ranked = self.foundation.rank(evaluations)
            evaluations_data = [r.model_dump() for r in ranked]
            
            # STOP GATE F - PRESCRIPTION / SELECTION AUTHORITY
            sel_auth = self.semantic_context.selection_authority
            
            if sel_auth and sel_auth.is_authorized():
                if sel_auth.authority_type.name == "HUMAN":
                    decision_status = "SELECTION_AUTHORIZED_HUMAN"
                else:
                    decision_status = "SELECTION_AUTHORIZED"
                
                # Check for Prescription authority absent (PATH E)
                if getattr(self.semantic_context, "prescription_authority", None) is None:
                    decision_status = "PENDING_PRESCRIPTION_AUTHORITY"
                    proposition_str = "PENDING_PRESCRIPTION_AUTHORITY"
                else:
                    proposition_str = f"DECISION_MADE: Alternative {ranked[0].alternative_id}"
            else:
                if sel_auth and sel_auth.authority_type.name == "LLM" and sel_auth.confirmation_status.name != "CONFIRMED":
                    decision_status = "SELECTION_AUTHORITY_REQUIRED"
                else:
                    decision_status = "PENDING_SELECTION_AUTHORITY"
                proposition_str = decision_status
        
        knowledge = Knowledge(
            identity=KnowledgeId(value=str(uuid.uuid4())),
            category=KnowledgeCategory.STRATEGIC,
            proposition=proposition_str,
            semantic_context=KnowledgeContext(process="Decision Making"),
            supporting_evidence=[],
            constraints=KnowledgeConstraints(),
            assumptions=KnowledgeAssumptions(assumptions=["Automatic argmax requires explicit selection authority"]),
            structured_data={
                "source_knowledge_id": str(predictive_k.identity.value),
                "prescription_status": "NOT_MATERIALIZED",
                "rationale_status": "NOT_MATERIALIZED",
                "decision_status": decision_status,
                "evaluations": evaluations_data,
                "builder_result": builder_result["status"] if builder_result else None
            },
            confidence=ConfidenceScore(value=1.0),
            traceability=trace_id,
            provenance=Provenance(
                source_document_id=DocumentId(value="mock-doc-prescriptor"),
                produced_by_module=ModuleId(value=self.em_id),
                produced_at=datetime.now(timezone.utc),
                produced_from="ScientificFoundation"
            )
        )
        return [knowledge]
