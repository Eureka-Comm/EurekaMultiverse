from typing import Protocol, runtime_checkable
from .models import AgentRequest, AgentResponse

@runtime_checkable
class AgentProvider(Protocol):
    """
    Protocol defining the fundamental boundary between the EUREKA Cognitive Foundation
    and any external or internal LLM provider.
    
    Implementations of this protocol MUST NOT mutate EUREKA Knowledge Packages,
    grant authorities, or modify semantic contexts directly.
    """
    
    def generate(self, request: AgentRequest) -> AgentResponse:
        """
        Executes a stateless generation request against the provider.
        
        Args:
            request: The provider-agnostic request.
            
        Returns:
            AgentResponse: The strictly typed response containing UNTRUSTED COGNITIVE OUTPUT.
        """
        ...
