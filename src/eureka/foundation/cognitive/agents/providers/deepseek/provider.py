import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional
from ...models import AgentRequest, AgentResponse, AgentToolCall
from ...contracts import AgentProvider
from ...config import AgentRuntimeConfig

class DeepSeekAgentProvider(AgentProvider):
    """
    Implements the DeepSeek agent provider using raw HTTP to maintain isolation
    from the openai SDK.
    """
    
    def __init__(self, config: AgentRuntimeConfig):
        self.config = config
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_url = "https://api.deepseek.com/chat/completions"

    def generate(self, request: AgentRequest) -> AgentResponse:
        # Cost safety gate
        if not self.config.external_network_enabled:
            raise RuntimeError("BLOCKED: External network is disabled in the runtime config. To use DeepSeek API, you must explicitly enable external_network.")
            
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_UNAVAILABLE: The DEEPSEEK_API_KEY environment variable is missing.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Build payload compatible with DeepSeek/OpenAI chat completions
        messages = []
        if request.system_context:
            messages.append({"role": "system", "content": request.system_context})
            
        messages.extend(request.messages)
        
        payload = {
            "model": request.model,
            "messages": messages,
        }
        
        if request.tools:
            payload["tools"] = request.tools
            
        if request.response_format:
            payload["response_format"] = request.response_format
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.api_url, data=data, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req) as response:
                response_body = response.read().decode('utf-8')
                result = json.loads(response_body)
                
                choice = result.get("choices", [{}])[0]
                message = choice.get("message", {})
                
                content = message.get("content")
                finish_reason = choice.get("finish_reason", "unknown")
                
                # Parse tool calls if present
                tool_calls = None
                raw_tool_calls = message.get("tool_calls")
                if raw_tool_calls:
                    tool_calls = []
                    for tc in raw_tool_calls:
                        tool_calls.append(AgentToolCall(
                            id=tc.get("id", ""),
                            name=tc.get("function", {}).get("name", ""),
                            arguments=tc.get("function", {}).get("arguments", "{}")
                        ))
                
                usage = result.get("usage", {})
                
                return AgentResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=finish_reason,
                    provider="DEEPSEEK",
                    model=request.model,
                    usage=usage,
                    traceability_id=request.request_id,
                    provenance={
                        "source": "DeepSeekAPI",
                        "api_url": self.api_url,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"DeepSeek API Error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"DeepSeek Request Failed: {str(e)}")
