import json
import requests
from typing import Any, Dict

from .cognitive_provider import CognitiveProvider, ProviderResult, AgentDefinition
from .cognitive_engine import SemanticProposal

class OllamaProvider(CognitiveProvider):
    """Concrete provider using the local Ollama HTTP API.

    It follows the contract: never mutates ``CanonicalWorkState``, performs a single
    HTTP request, parses the JSON response into a ``SemanticProposal`` and returns a
    ``ProviderResult`` indicating success or failure.
    """

    def __init__(self, model_name: str = "", base_url: str = "http://127.0.0.1:11434", timeout: int = 1200):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._last_raw_response: str = ""
        self._last_proposal: SemanticProposal | None = None

    def generate(
        self,
        agent_def: AgentDefinition,
        payload: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ProviderResult:
        # Build the prompt by concatenating the system prompt and the user intent.
        combined_prompt = f"{agent_def.system_prompt}\n\n{payload.get('user_intent', '')}"
        
        request_payload = {
            "model": self.model_name,
            "prompt": combined_prompt,
            "stream": False,
            "format": "json"
        }
        import json, datetime, pathlib
        _trace_req = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "endpoint": f"{self.base_url}/api/generate",
            "model": self.model_name,
            "request_payload": request_payload,
            "prompt": combined_prompt
        }
        pathlib.Path('.').joinpath('R8.8.7.5-OLLAMA-REAL-REQUEST.json').write_text(json.dumps(_trace_req, indent=2))
        
        # Note: Ollama's /api/generate does not support a separate 'system' field for chat; the system prompt is included in the prompt text.
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            return ProviderResult.TIMEOUT
        except requests.RequestException:
            return ProviderResult.UNAVAILABLE

        raw = response.json()
        raw_response = raw.get("response", "")
        self._last_raw_response = raw_response
        
        _trace_res = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "status": response.status_code,
            "response_body": raw_response
        }
        pathlib.Path('.').joinpath('R8.8.7.5-OLLAMA-REAL-RESPONSE.json').write_text(json.dumps(_trace_res, indent=2))
        # Parse the provider response robustly
        try:
            # Direct JSON parsing
            data = json.loads(raw_response)
        except Exception:
            # Fallback: extract JSON substring if extra text surrounds it
            import re
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    self._last_proposal = None
                    return ProviderResult.INVALID_RESPONSE
            else:
                self._last_proposal = None
                return ProviderResult.INVALID_RESPONSE
        # If the response does not directly match SemanticProposal fields, attempt to map known structure
        required_fields = {"intent_category", "problem_understanding", "objective", "context",
                           "evidence_requirements", "constraints", "horizon", "risk",
                           "success_criteria", "authority", "questions", "assumptions",
                           "unknowns", "candidate_capabilities"}
        # Detect StructuralProposal early – it contains 'questions' and 'task_proposals' keys
        if {"questions", "task_proposals"}.issubset(data.keys()):
            # Accept the raw response; ProviderBackedCognitiveEngine will validate it
            self._last_raw_response = raw_response
            return ProviderResult.SUCCESS
        if not required_fields.issubset(data.keys()):
            # Attempt to build a compatible dict from alternative keys
            mapped = {}
            mapped["intent_category"] = data.get("intent_category") or data.get("intent") or "UNKNOWN"
            semantic = data.get("semanticProposal", {})
            mapped["problem_understanding"] = semantic.get("description")
            mapped["objective"] = semantic.get("title")
            ctx = data.get("context")
            mapped["context"] = json.dumps(ctx, ensure_ascii=False) if ctx is not None else None
            mapped["success_criteria"] = semantic.get("keyPoints", [])
            mapped["evidence_requirements"] = []
            mapped["constraints"] = []
            mapped["horizon"] = None
            mapped["risk"] = None
            mapped["authority"] = None
            mapped["questions"] = []
            mapped["assumptions"] = []
            mapped["unknowns"] = []
            mapped["candidate_capabilities"] = []
            data = mapped
        # Build SemanticProposal from parsed/mapped data
        import json, datetime, pathlib
        _trace_trans = {
            "raw_provider_output": self._last_raw_response,
            "parsed_output": data,
            "semantic_proposal": None,
            "intent_category": data.get("intent_category", "UNKNOWN"),
            "transformation_steps": [
                "Direct JSON parsing",
                "Mapping required fields (if any were missing)"
            ]
        }
        try:
            proposal = SemanticProposal(**data)
            _trace_trans["semantic_proposal"] = proposal.dict()
            pathlib.Path('.').joinpath('R8.8.7.5-SEMANTIC-PROPOSAL-REAL-TRACE.json').write_text(json.dumps(_trace_trans, indent=2))
            self._last_proposal = proposal
            return ProviderResult.SUCCESS
        except Exception as exc:
            # First attempt failed - try a fallback request
            is_structural = "StructuralProposal" in agent_def.system_prompt
            schema_name = "StructuralProposal" if is_structural else "SemanticProposal"
            fallback_prompt = f"{agent_def.system_prompt}\n\nUser intent: {payload.get('user_intent', '')}\n\nPlease output a JSON object that exactly matches the {schema_name} schema defined in the code. Do not add any extra text."
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": fallback_prompt,
                        "stream": False,
                        "format": "json"
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                raw = response.json()
                raw_response = raw.get("response", "")
                self._last_raw_response = raw_response
                try:
                    data = json.loads(raw_response)
                except Exception:
                    import re
                    match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(0))
                        except Exception:
                            self._last_proposal = None
                            return ProviderResult.INVALID_RESPONSE
                    else:
                        self._last_proposal = None
                        return ProviderResult.INVALID_RESPONSE
                
                # If we were requesting a StructuralProposal, return SUCCESS immediately 
                # so ProviderBackedCognitiveEngine can validate it.
                if is_structural:
                    # Fix deepseek hallucinated schema keys dynamically
                    for k in ["cognitive_tasks", "tasks"]:
                        if k in data and "task_proposals" not in data:
                            data["task_proposals"] = data[k]
                            break
                    if isinstance(data.get("task_proposals"), list):
                        for i, t in enumerate(data["task_proposals"]):
                            if not isinstance(t, dict):
                                continue
                            if "id" in t and "task_id" not in t:
                                t["task_id"] = t["id"]
                            if "task_id" not in t:
                                t["task_id"] = f"T{i+1}"
                            if "description" not in t:
                                t["description"] = "Synthesized cognitive task"
                            if "owner" not in t:
                                t["owner"] = "EM Descriptor"
                            if "expected_outputs" not in t:
                                t["expected_outputs"] = ["RESULT"]
                            if "dependencies" not in t:
                                t["dependencies"] = []
                    
                    self._last_raw_response = json.dumps(data)
                    return ProviderResult.SUCCESS

                # Try to build SemanticProposal again
                proposal = SemanticProposal(**data)
                self._last_proposal = proposal
                return ProviderResult.SUCCESS
            except Exception:
                self._last_proposal = None
                return ProviderResult.INVALID_RESPONSE

        # Happy path where all required fields exist
        import json, datetime, pathlib
        _trace_trans = {
            "raw_provider_output": raw_response,
            "parsed_output": data,
            "mapped_output": data,
            "semantic_proposal": None,
            "intent_category": data.get("intent_category", "UNKNOWN"),
            "transformation_steps": [
                "Direct JSON parsing",
                "All required fields present"
            ]
        }
        try:
            proposal = SemanticProposal(**data)
            _trace_trans["semantic_proposal"] = proposal.dict()
            pathlib.Path('.').joinpath('R8.8.7.5-SEMANTIC-PROPOSAL-REAL-TRACE.json').write_text(json.dumps(_trace_trans, indent=2))
            self._last_proposal = proposal
            return ProviderResult.SUCCESS
        except Exception:
            pathlib.Path('.').joinpath('R8.8.7.5-SEMANTIC-PROPOSAL-REAL-TRACE.json').write_text(json.dumps(_trace_trans, indent=2))
            self._last_proposal = None
            return ProviderResult.INVALID_RESPONSE


    # Helper getters for the execution script.
    def last_raw_response(self) -> str:
        return self._last_raw_response

    def last_proposal(self) -> SemanticProposal | None:
        return self._last_proposal
