import json
import datetime
import pathlib
from typing import Dict, Any

from .cognitive_provider import CognitiveProvider, ProviderResult
from .agent_definition import AgentDefinition
from .cognitive_engine import CognitiveEngine, SemanticProposal, StructuralProposal, DescriptorProposal

class ProviderBackedCognitiveEngine(CognitiveEngine):
    """Thin wrapper that uses a :class:`CognitiveProvider` to generate proposals.

    Only the ``propose_problem`` method is required for the R8.1.2 loop.
    ``propose_structure`` returns an empty ``StructuralProposal`` to keep the
    orchestration pipeline alive without adding new architecture.
    """

    def __init__(self, provider: CognitiveProvider):
        self.provider = provider

    def propose_problem(self, user_intent: str) -> SemanticProposal:
        payload = {"user_intent": user_intent}
        context = {}
        agent_def = AgentDefinition(
            agent_id="ollama_provider",
            version="1.0",
            system_prompt=(
                "You are a cognitive assistant. Given the user's intent, output a JSON object exactly matching the SemanticProposal schema. "
                "intent_category debe ser exactamente uno de los valores permitidos: EXPLORATORY, GOAL_ORIENTED, TROUBLESHOOTING, ANALYTICAL, UNKNOWN. "
                "No crear categorías nuevas. No traducir nombres. No utilizar etiquetas descriptivas. "
                "Seleccionar la categoría que corresponda al significado del intent según las definiciones proporcionadas. "
                "The fields must be strictly typed as follows: "
                "intent_category (string), problem_understanding (string), objective (string), context (string), "
                "horizon (string), risk (string), authority (string), "
                "evidence_requirements (list of strings), constraints (list of strings), "
                "success_criteria (list of strings), questions (list of strings), assumptions (list of strings), "
                "unknowns (list of strings), candidate_capabilities (list of strings). "
                "Do not include any extra text or explanations."
            ),
            input_schema={"type": "object", "properties": {"user_intent": {"type": "string"}}},
            output_schema={"type": "object"},
            capabilities=[],
            forbidden_operations=[],
            knowledge_sources=[],
            provider_policy={"timeout": getattr(self.provider, "timeout", 120)},
        )
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            # Trace provider input (payload and agent definition)
            import json, datetime, pathlib
            _trace_input = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "stage": "provider_input",
                "agent_def": {
                    "agent_id": agent_def.agent_id,
                    "system_prompt": agent_def.system_prompt
                },
                "payload": payload
            }
            pathlib.Path('.').joinpath('R8.8.7.5-PROVIDER-INPUT-TRACE.json').write_text(json.dumps(_trace_input, indent=2))
            
            result = self.provider.generate(agent_def, payload, context)

            if result == ProviderResult.SUCCESS:
                break
            if result == ProviderResult.TIMEOUT:
                if attempt < max_retries:
                    print(f"Provider timeout on attempt {attempt}, retrying...")
                    continue
                else:
                    raise RuntimeError(f"Provider failed with {result} after {attempt} attempts")
            else:
                raise RuntimeError(f"Provider failed with {result}")
        # After loop, ensure success
        if result != ProviderResult.SUCCESS:
            raise RuntimeError(f"Provider failed with {result}")
        # After obtaining proposal, trace the raw response and parsed proposal
        raw_resp = self.provider.last_raw_response()
        proposal_obj = self.provider.last_proposal()
        import json, datetime, pathlib
        _trace_response = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "stage": "provider_response",
            "raw_response": raw_resp,
            "proposal": json.loads(json.dumps(proposal_obj.dict())) if proposal_obj else None
        }
        pathlib.Path('.').joinpath('R8.8.7.5-OLLAMA-RESPONSE-TRACE.json').write_text(json.dumps(_trace_response, indent=2))
        # Return the proposal as before

        proposal = proposal_obj
        if not proposal:
            raise RuntimeError("Provider did not produce a SemanticProposal")
        return proposal

    def propose_structure(self, problem) -> StructuralProposal:
        """Generate a StructuralProposal using the existing OllamaProvider.

        Steps:
        1. Build a system prompt that asks the model to output a JSON matching the
           StructuralProposal schema (questions, entities, variables, relationships,
           assumptions, unknowns, evidence_requirements, constraints, success_criteria,
           task_proposals). No extra text is allowed.
        2. Use the existing OllamaProvider (passed in at construction) with model
           "deepseek-r1:14b".
        3. Send the problem model JSON as the user intent payload.
        4. Retrieve the raw response, parse it as JSON, and validate it by
           constructing a StructuralProposal instance.
        5. On any failure (timeout, provider error, invalid JSON, validation error)
           raise RuntimeError("FAIL_CLOSED: ...").
        """
        # Build the system prompt - must request a pure JSON StructuralProposal
        system_prompt = """
        You are a cognitive assistant for EUREKA. 
        Your job is to parse the Governed Problem Model and output a JSON matching the StructuralProposal schema.
        You must propose CognitiveTasks that break down the work, assigning an owner (e.g. EM Descriptor, EM Predictor) and specifying expected_outputs and dependencies (using task_ids).
        DO NOT assume an execution pipeline. The network must be dynamically tailored to the problem.
        """

        # Create agent definition for the provider call
        agent_def = AgentDefinition(
            agent_id="ollama_provider",
            version="1.0",
            system_prompt=system_prompt,
            input_schema={"type": "object", "properties": {"user_intent": {"type": "string"}}},
            output_schema={"type": "object"},
            capabilities=[],
            forbidden_operations=[],
            knowledge_sources=[],
            provider_policy={"timeout": getattr(self.provider, "timeout", 1800)},
        )
        # Payload: send the full ProblemModel JSON as the user intent
        payload = {"user_intent": problem.model_dump_json()}
        context = {}
        # Perform the provider call with retries (max 2 as in propose_problem)
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            result = self.provider.generate(agent_def, payload, context)
            if result == ProviderResult.SUCCESS:
                break
            if result == ProviderResult.TIMEOUT:
                if attempt < max_retries:
                    continue
                else:
                    raise RuntimeError("FAIL_CLOSED: Provider timeout after retries")
            else:
                raise RuntimeError(f"FAIL_CLOSED: Provider failed with {result}")
        # Retrieve raw response
        raw_response = self.provider.last_raw_response()
        if not raw_response:
            raise RuntimeError("FAIL_CLOSED: Empty raw response from provider")
        # Parse JSON safely – reuse logic from OllamaProvider if needed
        try:
            data = json.loads(raw_response)
        except Exception:
            # Fallback: extract JSON substring
            import re
            match = re.search(r"\\{.*\\}", raw_response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception as e:
                    raise RuntimeError(f"FAIL_CLOSED: Invalid JSON in provider response: {e}")
            else:
                raise RuntimeError("FAIL_CLOSED: No JSON found in provider response")
        # Validate against StructuralProposal model
        try:
            proposal = StructuralProposal(**data)
        except Exception as e:
            raise RuntimeError(f"FAIL_CLOSED: StructuralProposal validation failed: {e}")
        return proposal
        return StructuralProposal(task_proposals=[])

    def propose_findings(self, problem, task, evidence_units) -> DescriptorProposal:
        agent_def = AgentDefinition(
            role="EM Descriptor",
            system_prompt="""
            You are EM Descriptor for EUREKA. Your task is to extract findings from the provided evidence.
            You must output a JSON object exactly matching the DescriptorProposal schema.
            The JSON MUST contain:
            - candidate_findings: A list of objects, each with 'statement' (string), 'finding_type' (string, e.g. "DESCRIPTIVE"), 'evidence_refs' (list of strings), and optionally 'method'.
            - limitations: A list of strings.
            Do not output any extra text.
            """,
            input_schema={"type": "object"}, output_schema={"type": "object"},
            capabilities=[], forbidden_operations=[], knowledge_sources=[], provider_policy={}
        )
        
        evidence_str = ""
        for i, e in enumerate(evidence_units):
            if isinstance(e, str):
                evidence_str += f"Evidence {i+1}: {e}\n"
            elif hasattr(e, 'text_blocks'):
                blocks = " ".join([str(b) for b in getattr(e, 'text_blocks', [])])
                evidence_str += f"Evidence {getattr(e, 'evidence_id', i+1)}: {blocks}\n"
        
        payload = {
            "task_description": getattr(task, "description", ""),
            "evidence": evidence_str
        }
        
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            result = self.provider.generate(agent_def, payload, {})
            if result == ProviderResult.SUCCESS:
                break
            if result == ProviderResult.TIMEOUT and attempt < max_retries:
                continue
            raise RuntimeError(f"FAIL_CLOSED: Provider failed with {result}")
            
        raw_response = self.provider.last_raw_response()
        try:
            data = json.loads(raw_response)
        except Exception:
            import re
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception as e:
                    raise RuntimeError(f"FAIL_CLOSED: Invalid JSON in provider response: {e}")
            else:
                raise RuntimeError("FAIL_CLOSED: No JSON found in provider response")
                
        # Handle hallucinations
        for k in ["findings", "candidate_findings"]:
            if k in data:
                data["candidate_findings"] = data.pop(k)
                break
                
        if "candidate_findings" not in data:
            data["candidate_findings"] = []
            
        for f in data.get("candidate_findings", []):
            if not isinstance(f, dict): continue
            if "statement" not in f:
                f["statement"] = str(f)
            if "finding_type" not in f:
                f["finding_type"] = "DESCRIPTIVE"
            if "evidence_refs" not in f:
                f["evidence_refs"] = []
                
        try:
            return DescriptorProposal(**data)
        except Exception as e:
            raise RuntimeError(f"FAIL_CLOSED: DescriptorProposal validation failed: {e}")

    def propose_predictions(self, *args, **kwargs):
        raise NotImplementedError

    def propose_prescription(self, *args, **kwargs):
        raise NotImplementedError

    def propose_action_plan(self, *args, **kwargs):
        raise NotImplementedError

    def propose_publication(self, *args, **kwargs):
        raise NotImplementedError
