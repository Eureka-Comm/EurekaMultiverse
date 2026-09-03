from typing import Dict, List
from eureka_cognitive_sdk.core.exceptions.enterprise import EnterpriseError
from eureka.foundation.cognitive.contracts.em_contract import EMExecutionContract
from eureka.foundation.cognitive.contracts.intent import EnterpriseIntent

class EMRegistry:
    """
    Registry for Enterprise Modules (EMs).
    Provides discovery and fail-closed resolution of Cognitive Execution Contracts.
    """
    def __init__(self):
        self._ems: Dict[str, EMExecutionContract] = {}

    def register(self, em: EMExecutionContract) -> None:
        if not isinstance(em, EMExecutionContract):
            raise EnterpriseError("Invalid EM: Must implement EMExecutionContract")
        if not em.em_id:
            raise EnterpriseError("Invalid EM: em_id cannot be empty")
        if em.em_id in self._ems:
            raise EnterpriseError(f"Duplicate registration: EM {em.em_id} is already registered")
        
        self._ems[em.em_id] = em

    def resolve(self, em_id: str) -> EMExecutionContract:
        if em_id not in self._ems:
            raise EnterpriseError(f"Unknown EM: {em_id} is not registered")
        return self._ems[em_id]

    def discover(self, intent: EnterpriseIntent) -> List[EMExecutionContract]:
        """
        Discover candidate EMs that are semantically capable of fulfilling the intent.
        """
        candidates = []
        for em in self._ems.values():
            meta = em.get_semantic_metadata()
            if intent.objective in meta.supported_objectives and intent.domain == meta.semantic_domain:
                candidates.append(em)
        return candidates

    def contains(self, em_id: str) -> bool:
        return em_id in self._ems

    def list(self) -> List[str]:
        return list(self._ems.keys())
