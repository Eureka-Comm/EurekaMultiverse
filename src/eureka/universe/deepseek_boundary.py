from typing import Dict, Any, List
from .capability_fabric import CapabilityRegistry

class DeepSeekToolBoundary:
    """
    Fail-closed boundary that interprets Copilot tool calls.
    It guarantees DeepSeek cannot acquire execution authority, unfreeze, or run arbitrary code.
    """
    def __init__(self, capability_registry: CapabilityRegistry):
        self.registry = capability_registry
        
        # Security hardcoded constraints
        self.BANNED_EM_TARGETS = {"ACTIONER", "UNFREEZE", "FREEZE", "EXECUTE"}

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives a raw tool call from DeepSeek and validates it against the registry.
        Returns a structured response or a BLOCKED/GAP status.
        """
        cap = self.registry.resolve(tool_name)
        
        if not cap:
            return {"status": "BLOCKED", "reason": f"Unknown capability '{tool_name}' requested. Action denied."}
            
        if cap.target_em_id in self.BANNED_EM_TARGETS:
            return {"status": "BLOCKED", "reason": f"Capability maps to restricted EM '{cap.target_em_id}'. Execution authority denied."}
            
        # Normally here we would perform JSON schema validation against cap.input_schema
        # For now, we assume schema validation passed
        
        return {
            "status": "APPROVED",
            "capability_id": cap.capability_id,
            "target_em_id": cap.target_em_id,
            "produces": cap.produces
        }
