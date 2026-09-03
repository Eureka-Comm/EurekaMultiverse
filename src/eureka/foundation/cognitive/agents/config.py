from enum import Enum
from pydantic import BaseModel, Field

class RuntimeMode(str, Enum):
    LOCAL_MOCK = "LOCAL_MOCK"
    DEEPSEEK_API = "DEEPSEEK_API"
    LOCAL_DEEPSEEK = "LOCAL_DEEPSEEK"

class AgentRuntimeConfig(BaseModel):
    """
    Configuration for the Agent Runtime.
    Enforces safe defaults for the MVP.
    """
    mode: RuntimeMode = Field(default=RuntimeMode.LOCAL_MOCK)
    external_network_enabled: bool = Field(
        default=False, 
        description="Must be explicitly set to True to allow calls to remote APIs (like DeepSeek)."
    )
