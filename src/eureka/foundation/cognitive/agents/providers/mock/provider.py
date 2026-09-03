import json
from datetime import datetime, timezone
from typing import Optional, Callable
from ...models import AgentRequest, AgentResponse, AgentToolCall
from ...contracts import AgentProvider

class MockAgentProvider(AgentProvider):
    """
    Deterministically returns predefined responses for testing the runtime integration
    and the EUREKA Governance boundaries without incurring API costs.
    """
    
    def __init__(self):
        self._responses = {}
        self._default_response_factory = self._basic_default

    def register_mock_response(self, prompt_keyword: str, response: AgentResponse):
        """Registers a specific response to be returned if the prompt matches a keyword."""
        self._responses[prompt_keyword] = response
        
    def set_default_factory(self, factory: Callable[[AgentRequest], AgentResponse]):
        """Sets a factory function to generate dynamic but deterministic defaults."""
        self._default_response_factory = factory

    def generate(self, request: AgentRequest) -> AgentResponse:
        # Check if we have a registered response matching any keyword in the messages
        content_str = " ".join([m.get("content", "") for m in request.messages])
        
        for keyword, response in self._responses.items():
            if keyword in content_str:
                # Need to update the trace_id to match the request
                return AgentResponse(
                    content=response.content,
                    tool_calls=response.tool_calls,
                    finish_reason=response.finish_reason,
                    provider="MOCK",
                    model=request.model,
                    usage=response.usage,
                    traceability_id=request.request_id,
                    provenance=response.provenance
                )
                
        return self._default_response_factory(request)
        
    def _basic_default(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(
            content="MOCK_RESPONSE: The system is operating normally. I am a mock.",
            finish_reason="stop",
            provider="MOCK",
            model=request.model,
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            traceability_id=request.request_id,
            provenance={
                "source": "MockAgentProvider",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
