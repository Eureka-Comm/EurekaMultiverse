from typing import Dict, Optional, Type
from .contracts import AgentProvider
from .config import AgentRuntimeConfig, RuntimeMode
from .providers.mock.provider import MockAgentProvider
from .providers.deepseek.provider import DeepSeekAgentProvider

class AgentProviderRegistry:
    """
    Registry for instantiating the appropriate AgentProvider based on runtime configuration.
    """
    
    def __init__(self, config: AgentRuntimeConfig):
        self.config = config
        
    def get_provider(self) -> AgentProvider:
        """
        Resolves the AgentProvider according to the configured RuntimeMode.
        """
        if self.config.mode == RuntimeMode.LOCAL_MOCK:
            return MockAgentProvider()
            
        elif self.config.mode == RuntimeMode.DEEPSEEK_API:
            return DeepSeekAgentProvider(self.config)
            
        elif self.config.mode == RuntimeMode.LOCAL_DEEPSEEK:
            # Future expansion for local VLLM/Ollama running deepseek-coder/chat
            raise NotImplementedError("LOCAL_DEEPSEEK is a planned capability but not yet implemented.")
            
        else:
            raise ValueError(f"Unknown RuntimeMode: {self.config.mode}")
