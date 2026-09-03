from typing import List, Dict

from eureka_cognitive_sdk.ekp.package import EnterpriseKnowledgePackage
from eureka_cognitive_sdk.ekp.artifacts.knowledge import Knowledge
from eureka.foundation.cognitive.contracts.em_contract import EMExecutionContract
from eureka.foundation.cognitive.contracts.capability_requirement import CapabilityRequirement
from eureka.foundation.scientific.runtime.assembly import ExecutableRuntimeCapability
from eureka_cognitive_sdk.core.identifiers.trace_id import TraceId
from eureka.math.operators import Disjunction
from eureka.math.generators import CMTGenerator001, CMTInverseGenerator001


class EMPredictorEngine(EMExecutionContract):
    """EMPredictorEngine implements the minimal integration contract.

    - No capability requirements in the contract.
    - Prediction semantics are now provided by a real mathematical capability.
    - No mutation of the EKP.
    """

    @property
    def em_id(self) -> str:
        return "empredictor"

    def get_capability_requirements(self) -> List[CapabilityRequirement]:
        # Require the disjunction capability based on CMTGenerator001.
        from eureka.foundation.cognitive.contracts.capability_requirement import CapabilityRequirement
        return [CapabilityRequirement(requirement_id="req1", capability_type="DISJUNCTION-CMT-001", semantic_role="aggregation", version=None)]

    def get_semantic_metadata(self):
        # Use the default EMSemanticMetadata as defined in EMExecutionContract.
        return super().get_semantic_metadata()

    def _build_capability(self) -> Disjunction:
        """Instantiate a Disjunction operator with concrete generator and inverse.

        This uses the certified primitives defined in `generators.py` and
        `operators.py`. No dynamic code compilation is required for this
        primitive capability.
        """
        generator = CMTGenerator001()
        inverse = CMTInverseGenerator001()
        return Disjunction(generator, inverse)

    def execute(
        self,
        ekp: EnterpriseKnowledgePackage,
        capabilities: Dict[str, ExecutableRuntimeCapability],
        trace_id: TraceId,
    ) -> List[Knowledge]:
        """Execute the predictor using a real mathematical aggregation.

        The EKP is expected to expose an iterable of truth values via a `values`
        attribute. If absent, a default deterministic sample is used.
        """
        cap_name = "DISJUNCTION-CMT-001"
        if cap_name in capabilities:
            disjunction_cap = capabilities[cap_name].get_callable()
        else:
            disjunction_cap = self._build_capability()

        # Retrieve truth values from EKP knowledge artifacts
        if ekp.knowledge is None or len(ekp.knowledge) == 0:
            raise RuntimeError("EKP must provide a non-empty KnowledgeCollection to predict upon.")

        raw_values = []
        for k in ekp.knowledge:
            val = k.structured_data.get("value")
            if val is not None and isinstance(val, (int, float)):
                raw_values.append(float(val))

        # Fail-closed if no valid truth values were found
        if len(raw_values) == 0:
            raise RuntimeError("EKP knowledge artifacts must contain at least one valid truth value in structured_data['value'].")

        # Domain validation for CMTGenerator001: 0 < x <= 1
        for v in raw_values:
            if not (0.0 < v <= 1.0):
                raise RuntimeError(f"Truth value {v} out of allowed domain (0, 1].")
        truth_values = raw_values

        # Execute the capability
        if hasattr(disjunction_cap, "aggregate"):
            result_value = disjunction_cap.aggregate(truth_values)
        else:
            # Compiled capability exposes a standard evaluation function.
            # Map inputs to kwargs v1, v2, v3 for the primitive compiler.
            kwargs = {f"v{i+1}": val for i, val in enumerate(truth_values)}
            result_value = disjunction_cap(**kwargs)
                # Build the canonical proposition string as per G3 contract
        # Format: <capability_id>(<input_list>) = <numeric_result>
        # Input list is the list of raw truth values used for the aggregation
        proposition_str = f"{cap_name}({raw_values}) = {result_value}"
        
        from eureka_cognitive_sdk.core.identifiers.knowledge_id import KnowledgeId
        from eureka_cognitive_sdk.core.value_objects.enumerations import KnowledgeCategory
        from eureka_cognitive_sdk.ekp.artifacts.knowledge import KnowledgeContext, KnowledgeConstraints, KnowledgeAssumptions
        import uuid
        from eureka_cognitive_sdk.core.value_objects.primitives import ConfidenceScore
        from eureka_cognitive_sdk.core.identifiers.document_id import DocumentId
        from eureka_cognitive_sdk.core.identifiers.module_id import ModuleId
        from eureka_cognitive_sdk.ekp.provenance import Provenance
        from datetime import datetime, timezone
        
        knowledge = Knowledge(
            identity=KnowledgeId(value=str(uuid.uuid4())),
            category=KnowledgeCategory.OPERATIONAL,
            proposition=proposition_str,
            semantic_context=KnowledgeContext(),
            supporting_evidence=[],
            constraints=KnowledgeConstraints(),
            assumptions=KnowledgeAssumptions(),
            structured_data={"value": result_value},
            confidence=ConfidenceScore(value=1.0),
            traceability=trace_id,
            provenance=Provenance(
                source_document_id=DocumentId(value="mock-doc"),
                produced_by_module=ModuleId(value=self.em_id),
                produced_at=datetime.now(timezone.utc),
                produced_from="DISJUNCTION-CMT-001"
            )
        )
        return [knowledge]
