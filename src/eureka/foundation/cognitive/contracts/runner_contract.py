from abc import ABC, abstractmethod
from eureka_cognitive_sdk.ekp.package import EnterpriseKnowledgePackage
from eureka_cognitive_sdk.core.utilities.result import Result
from eureka_cognitive_sdk.core.exceptions.enterprise import EnterpriseError

class IGenericEMRunner(ABC):
    @abstractmethod
    def run(self, em_id: str, ekp: EnterpriseKnowledgePackage) -> Result[EnterpriseKnowledgePackage, EnterpriseError]:
        pass
