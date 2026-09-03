from abc import ABC, abstractmethod
from eureka_cognitive_sdk.core.identifiers.trace_id import TraceId
from typing import List, Dict
from eureka_cognitive_sdk.ekp.package import EnterpriseKnowledgePackage
from eureka_cognitive_sdk.ekp.artifacts.knowledge import Knowledge
from src.eureka.foundation.scientific.runtime.assembly import ExecutableRuntimeCapability
from .capability_requirement import CapabilityRequirement
from .em_semantic_metadata import EMSemanticMetadata

class EMExecutionContract(ABC):
    """
    Abstract Base Class that enforces generic behavior for any Enterprise Module.
    An EM must expose its identity, its capability requirements, its semantic metadata, and an execute method.
    """

    @property
    @abstractmethod
    def em_id(self) -> str:
        """Returns the unique identifier for this EM."""
        pass

    def get_semantic_metadata(self) -> EMSemanticMetadata:
        """Returns the semantic metadata used for discovery and planning."""
        return EMSemanticMetadata(
            supported_objectives=["ANY"],
            semantic_domain="DEFAULT",
            produced_knowledge_types=[],
            version="1.0"
        )
        
    @abstractmethod
    def get_capability_requirements(self) -> List[CapabilityRequirement]:
        """Declares the physical and semantic capabilities required by this EM"""
        pass
        
    @abstractmethod
    def execute(
        self,
        ekp: EnterpriseKnowledgePackage,
        capabilities: Dict[str, ExecutableRuntimeCapability],
        trace_id: TraceId
    ) -> List[Knowledge]:
        """
        Executes the EM logic using the provided resolved capabilities and the EKP.
        Returns a list of raw Knowledge artifacts (Provenance is injected by the Runner).
        capabilities is a dictionary keyed by requirement_id.
        """
        pass
