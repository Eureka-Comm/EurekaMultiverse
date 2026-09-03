from typing import List, Dict

from eureka.foundation.cognitive.contracts.em_contract import EMExecutionContract
from eureka.foundation.cognitive.contracts.capability_requirement import CapabilityRequirement
from eureka_cognitive_sdk.ekp.package import EnterpriseKnowledgePackage
from eureka_cognitive_sdk.core.identifiers.trace_id import TraceId
from eureka_cognitive_sdk.ekp.artifacts.knowledge import Knowledge

class EMDescriptor(EMExecutionContract):
    """Stub EM for Descriptor stage (no capabilities)."""

    @property
    def em_id(self) -> str:
        return "em_descriptor"

    def get_capability_requirements(self) -> List[CapabilityRequirement]:
        return []

    def execute(self, ekp: EnterpriseKnowledgePackage, capabilities: Dict[str, object], trace_id: TraceId) -> List[Knowledge]:
        return []
