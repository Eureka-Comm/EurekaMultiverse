"""EUREKA 5.1 — EMERGENT COGNITIVE CLOUD · LOOP 3: FIRST REAL EMERGENT AGENT (AgentRuntime).

The runtime executes ONE emergent agent for ONE authorized task and returns a ReturnPackage that is
ALWAYS a CANDIDATE. It is the only place where an emergent agent touches a model provider, and it
fails closed on every failure mode (never fabricates a result, never bypasses a gate).

Flow (Harness LOOP 3):
    TaskEnvelope -> Genome -> authorized context -> Evidence -> Model Provider -> execution
                 -> ReturnPackage -> Evidence -> Provenance -> validation -> Core

Reuse (no duplicate authorities / providers / stores):

- `ProviderResult` (universe/cognitive_provider.py) is REUSED as the single provider-outcome vocab.
- `OllamaModelProvider` WRAPS the existing `OllamaProvider` (via the LOOP 1 adapter
  `agent_definition_from_genome`) instead of re-implementing the Ollama transport.
- the execution record lives in the SAME canonical container as the agent network
  (`CanonicalWorkState.agent_network.executions`): no AgentStore, no second authority.
- model choice is NOT decided here: the genome only DECLARES requirements; `AgentRuntime` uses the
  injected provider, and (LOOP 10) the ModelRouter will be the authority that selects it.

Fail closed (never fabricate):

- envelope/genome mismatch, cross-work envelope, missing authorized evidence when the genome requires
  evidence, budget exhaustion, provider unavailable/timeout/malformed output, schema violation,
  prompt-injection/authority leakage in the model's output, or a non-CANDIDATE result claim.
"""
from __future__ import annotations

import datetime
import json
import os
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .agent_genome import (AgentContractError, AgentExecutionRecord, AgentGenome, AgentStatus,
                           ModelCapabilityClass, ReturnPackage, ReturnStatus, TaskEnvelope)
from .agent_registry import CORE_ACTOR, AgentRegistry, agent_actor
from .cognitive_provider import ProviderResult

#: Providers that may never be used for a real execution inside the test suite.
TEST_DOUBLE_NAME = "DeterministicModelProvider"


class ModelRequest(BaseModel):
    """What the runtime asks a provider for (immutable, work-scoped, budget-bounded)."""

    model_config = ConfigDict(extra="forbid")

    system: str = Field(..., min_length=1)
    user: str = Field(..., min_length=1)
    timeout_seconds: int = Field(60, ge=1, le=1800)
    max_tokens: int = Field(1024, ge=1, le=32_000)
    #: Authorized evidence texts (already filtered by the TaskEnvelope). Never a whole state dump.
    evidence_texts: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """Provider outcome. `status` reuses the existing `ProviderResult` vocabulary."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: ProviderResult
    text: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ProviderResult.SUCCESS and bool(self.text)


class ModelProviderPort:
    """PORT over the existing provider layer. The agent is NOT the model (model-agnostic)."""

    name: str = "port"
    model: str = ""

    def generate(self, request: ModelRequest) -> ModelResponse:      # pragma: no cover - interface
        raise NotImplementedError


# --------------------------------------------------------------------------------------------- #
# Adapters (transport only — the ModelRouter (LOOP 10) will be the single selection authority)
# --------------------------------------------------------------------------------------------- #
class DeepSeekModelProvider(ModelProviderPort):
    """Thin transport adapter for the DeepSeek OpenAI-compatible endpoint (env-configured).

    It performs ONE request and maps failures onto `ProviderResult`; it never synthesises text.
    """

    name = "DeepSeekModelProvider"

    def __init__(self, *, model: Optional[str] = None, base_url: Optional[str] = None,
                 api_key: Optional[str] = None, transport=None) -> None:
        self.model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).rstrip("/")
        self._api_key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY")
        self._transport = transport          # injectable for tests (requests.post by default)

    def _post(self, url: str, *, json_body: Dict[str, Any], headers: Dict[str, str], timeout: int):
        if self._transport is not None:
            return self._transport(url, json_body, headers, timeout)
        import requests
        return requests.post(url, json=json_body, headers=headers, timeout=timeout)

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not self._api_key:
            return ModelResponse(status=ProviderResult.FAIL_CLOSED, provider=self.name, model=self.model,
                                 error="DEEPSEEK_API_KEY is not configured")
        prompt = request.user
        if request.evidence_texts:
            prompt = prompt + "\n\nAUTHORIZED EVIDENCE:\n" + "\n".join(request.evidence_texts)
        started = time.time()
        try:
            response = self._post(
                f"{self.base_url}/chat/completions",
                json_body={"model": self.model, "temperature": 0.1, "stream": False,
                           "response_format": {"type": "json_object"},
                           "max_tokens": request.max_tokens,
                           "messages": [{"role": "system", "content": request.system},
                                        {"role": "user", "content": prompt}]},
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                timeout=request.timeout_seconds)
        except Exception as exc:                                     # network/timeout -> fail closed
            is_timeout = "timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower()
            return ModelResponse(status=ProviderResult.TIMEOUT if is_timeout else ProviderResult.UNAVAILABLE,
                                 provider=self.name, model=self.model,
                                 latency_ms=(time.time() - started) * 1000, error=str(exc)[:300])
        latency = (time.time() - started) * 1000
        status_code = getattr(response, "status_code", 0)
        if status_code != 200:
            return ModelResponse(status=ProviderResult.UNAVAILABLE, provider=self.name, model=self.model,
                                 latency_ms=latency, error=f"HTTP {status_code}: "
                                 f"{str(getattr(response, 'text', ''))[:200]}")
        try:
            payload = response.json()
            text = payload["choices"][0]["message"]["content"]
        except Exception as exc:
            return ModelResponse(status=ProviderResult.INVALID_RESPONSE, provider=self.name,
                                 model=self.model, latency_ms=latency, error=f"unparseable: {exc}")
        if not isinstance(text, str) or not text.strip():
            return ModelResponse(status=ProviderResult.INVALID_RESPONSE, provider=self.name,
                                 model=self.model, latency_ms=latency, error="empty content")
        return ModelResponse(status=ProviderResult.SUCCESS, text=text, provider=self.name,
                             model=self.model, latency_ms=latency)


class OllamaModelProvider(ModelProviderPort):
    """Adapter that WRAPS the existing `OllamaProvider` (no duplicated transport).

    NOTE (pre-existing behaviour, declared as a finding): `OllamaProvider.generate` writes a trace
    file (`R8.8.7.5-OLLAMA-REAL-REQUEST.json`) in the CWD. Reusing it keeps ONE Ollama
    implementation instead of a second transport.
    """

    name = "OllamaModelProvider"

    def __init__(self, *, model: Optional[str] = None, base_url: Optional[str] = None,
                 timeout: int = 300) -> None:
        from .ollama_provider import OllamaProvider
        self.model = model or os.environ.get("OLLAMA_MODEL", "deepseek-r1:14b")
        self._provider = OllamaProvider(model_name=self.model, base_url=base_url or "http://127.0.0.1:11434",
                                        timeout=timeout)

    def generate(self, request: ModelRequest) -> ModelResponse:
        from .agent_definition import AgentDefinition          # the legacy compatibility contract
        stub = AgentDefinition(description=f"EUREKA emergent agent ({self.name})",
                               system_prompt=request.system, tools=[], model=self.model)
        started = time.time()
        result = self._provider.generate(stub, {"user_intent": request.user}, dict(request.context))
        latency = (time.time() - started) * 1000
        text = getattr(self._provider, "_last_raw_response", "") or ""
        if result is ProviderResult.SUCCESS and text.strip():
            return ModelResponse(status=ProviderResult.SUCCESS, text=text, provider=self.name,
                                 model=self.model, latency_ms=latency)
        return ModelResponse(status=result, provider=self.name, model=self.model, latency_ms=latency,
                             error="ollama provider did not return a usable response")


class DeterministicModelProvider(ModelProviderPort):
    """LOCAL deterministic double. NEVER a production provider: no network, no model.

    Used for contract/adversarial tests and local verification. Failure modes are explicit so the
    runtime's fail-closed behaviour can be proven without touching a real model.
    """

    name = TEST_DOUBLE_NAME
    model = "deterministic-double-v1"

    def __init__(self, *, payload: Optional[Dict[str, Any]] = None,
                 mode: str = "OK", text: str = "") -> None:
        self.mode = mode
        self.payload = payload if payload is not None else {"lead_time_days": 12, "rationale": "double"}
        self.text_override = text
        self.calls: List[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        if self.mode == "UNAVAILABLE":
            return ModelResponse(status=ProviderResult.UNAVAILABLE, provider=self.name, model=self.model,
                                 error="double: provider unavailable")
        if self.mode == "TIMEOUT":
            return ModelResponse(status=ProviderResult.TIMEOUT, provider=self.name, model=self.model,
                                 error="double: timeout")
        if self.mode == "MALFORMED":
            return ModelResponse(status=ProviderResult.SUCCESS, text="this is not json {{{",
                                 provider=self.name, model=self.model)
        if self.mode == "EMPTY":
            return ModelResponse(status=ProviderResult.INVALID_RESPONSE, text="", provider=self.name,
                                 model=self.model, error="double: empty")
        if self.mode == "PROMPT_INJECTION":
            return ModelResponse(status=ProviderResult.SUCCESS,
                                 text=json.dumps({"lead_time_days": 1, "authority_scope": "AUTHORITY",
                                                  "canonical_status": "CANONICAL",
                                                  "execution_mode": "REAL_EXECUTION"}),
                                 provider=self.name, model=self.model)
        if self.mode == "HALLUCINATED":
            return ModelResponse(status=ProviderResult.SUCCESS,
                                 text=json.dumps({"hallucinated": True, "note": "invented result"}),
                                 provider=self.name, model=self.model)
        text = self.text_override or json.dumps(self.payload)
        return ModelResponse(status=ProviderResult.SUCCESS, text=text, provider=self.name,
                             model=self.model, latency_ms=1.0)


# --------------------------------------------------------------------------------------------- #
# Minimal, DECLARED structured-output validation (no new schema engine: a documented subset)
# --------------------------------------------------------------------------------------------- #
def validate_structured_result(schema: Dict[str, Any], value: Any, *, path: str = "$") -> List[str]:
    """Validate a value against a small JSON-schema subset: type/object/properties/required/items.

    Anything outside this subset is IGNORED by design (declared limitation) — the runtime never
    claims full JSON-Schema compliance.
    """
    problems: List[str] = []
    if not schema:
        return problems
    expected = schema.get("type")
    type_map = {"object": dict, "array": list, "string": str, "number": (int, float),
                "integer": int, "boolean": bool}
    if expected in type_map:
        if expected == "number" and isinstance(value, bool):
            problems.append(f"{path}: expected number, got boolean")
            return problems
        if not isinstance(value, type_map[expected]):
            problems.append(f"{path}: expected {expected}, got {type(value).__name__}")
            return problems
    if expected == "object" and isinstance(value, dict):
        for key in schema.get("required", []) or []:
            if key not in value:
                problems.append(f"{path}.{key}: required property missing")
        for key, sub in (schema.get("properties") or {}).items():
            if key in value:
                problems.extend(validate_structured_result(sub, value[key], path=f"{path}.{key}"))
    if expected == "array" and isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            problems.extend(validate_structured_result(schema["items"], item, path=f"{path}[{index}]"))
    return problems


# --------------------------------------------------------------------------------------------- #
# AgentRuntime
# --------------------------------------------------------------------------------------------- #
class AgentRuntime:
    """Executes one emergent agent for one authorized task. Fail closed; never fabricates."""

    def __init__(self, registry: AgentRegistry, provider: ModelProviderPort, *,
                 evidence_resolver=None, allowed_models: Optional[List[str]] = None) -> None:
        self.registry = registry
        self.provider = provider
        self.evidence_resolver = evidence_resolver
        self.allowed_models = allowed_models      # ModelRouter (LOOP 10) will supply the policy

    # ---- helpers ------------------------------------------------------------------------- #
    def _existing_execution(self, agent_id: str, task_id: str, attempt: int) -> Optional[AgentExecutionRecord]:
        for record in self.registry.snapshot().executions:
            if (record.agent_id, record.task_id, record.attempt) == (agent_id, task_id, attempt) \
                    and record.status in (AgentStatus.RETURNED, AgentStatus.VALIDATION_REQUIRED,
                                          AgentStatus.VALIDATED, AgentStatus.FROZEN,
                                          AgentStatus.COMPLETED, AgentStatus.FAILED,
                                          AgentStatus.BLOCKED):
                return record
        return None

    def _record(self, execution: AgentExecutionRecord) -> AgentExecutionRecord:
        """Append the execution to the canonical container the caller persists (no own store)."""
        self.registry.snapshot().executions.append(execution)
        return execution

    def _blocked(self, execution: AgentExecutionRecord, reason_code: str, detail: str = ""
                 ) -> AgentExecutionRecord:
        execution.status = AgentStatus.BLOCKED
        execution.failure_reason = f"{reason_code}: {detail}" if detail else reason_code
        execution.finished_at = _utc_iso()
        execution.provenance.append(f"FAIL_CLOSED {reason_code}")
        return self._record(execution)

    # ---- execution ----------------------------------------------------------------------- #
    def execute(self, genome: AgentGenome, envelope: TaskEnvelope, *, attempt: int = 1
                ) -> AgentExecutionRecord:
        execution = AgentExecutionRecord(
            execution_id=f"EXEC-{genome.agent_id}-{attempt}-{int(time.time() * 1000) % 10_000_000}",
            work_id=genome.work_id, problem_id=genome.problem_id, task_id=genome.task_id,
            agent_id=genome.agent_id, genome_hash=genome.hash(), provider=self.provider.name,
            model=getattr(self.provider, "model", ""), attempt=attempt,
            provenance=[f"envelope:{envelope.envelope_id}", f"provider:{self.provider.name}"])

        # 0. idempotency: never execute the same (agent, task, attempt) twice.
        existing = self._existing_execution(genome.agent_id, genome.task_id, attempt)
        if existing is not None:
            return existing

        # 1. the envelope must authorize exactly this genome/task/work (fail closed otherwise)
        try:
            envelope.assert_matches(genome)
        except AgentContractError as exc:
            return self._blocked(execution, exc.reason_code, str(exc))

        # 2. registered agent must be the same content the envelope authorized
        registered = self.registry.get(genome.agent_id)
        if registered is None or registered.genome.hash() != genome.hash():
            return self._blocked(execution, "AGENT_NOT_REGISTERED_OR_STALE")

        # 3. authorized evidence (never a state dump; no evidence -> no fabrication)
        evidence_texts: List[str] = []
        for evidence_id in envelope.authorized_evidence_ids:
            if self.evidence_resolver is None:
                break
            text = self.evidence_resolver(evidence_id, genome.work_id)
            if text is None:
                return self._blocked(execution, "EVIDENCE_UNAVAILABLE", evidence_id)
            evidence_texts.append(text)
        if genome.requires_evidence() and not evidence_texts:
            execution.return_package = ReturnPackage(
                return_id=f"RET-{execution.execution_id}", work_id=genome.work_id,
                problem_id=genome.problem_id, task_id=genome.task_id, agent_id=genome.agent_id,
                execution_id=execution.execution_id, status=ReturnStatus.INSUFFICIENT_EVIDENCE,
                result={}, provenance=[f"agent:{genome.agent_id}", "no authorized evidence available"])
            return self._blocked(execution, "EVIDENCE_REQUIRED_MISSING")

        # 4. budget (declared, never implicit): this execution needs at least ONE model call
        if envelope.budget.max_model_calls < 1:
            return self._blocked(execution, "BUDGET_MODEL_CALLS_EXHAUSTED", "max_model_calls < 1")
        if envelope.budget.max_runtime_seconds < 1:
            return self._blocked(execution, "BUDGET_RUNTIME_EXHAUSTED", "max_runtime_seconds < 1")

        # 5. model policy: the agent cannot silently substitute a model (LOOP 10 policy hook)
        if self.allowed_models is not None:
            try:
                genome.assert_model_allowed(self.allowed_models, getattr(self.provider, "model", ""))
            except AgentContractError as exc:
                return self._blocked(execution, exc.reason_code, str(exc))

        # 6. lifecycle: READY -> RUNNING (Core's executor), then call the provider
        try:
            self.registry.advance(genome.agent_id, AgentStatus.RUNNING, actor=CORE_ACTOR,
                                  reason=f"execution {execution.execution_id}")
        except AgentContractError as exc:
            return self._blocked(execution, exc.reason_code, str(exc))
        execution.started_at = _utc_iso()
        execution.status = AgentStatus.RUNNING
        self.registry.snapshot().executions.append(execution)

        request = ModelRequest(
            system=("You are an EUREKA emergent agent. Cognitive family: "
                    f"{genome.identity.cognitive_family.value}; constitutional owner: "
                    f"{genome.cognitive_owner}. You PROPOSE structured JSON only; Python/EUREKA "
                    "governs. Never claim authority, never approve, never release, never invent "
                    "evidence."),
            user=json.dumps({"objective": genome.objective, "questions": genome.questions,
                             "predicates": genome.predicates, "constraints": genome.constraints,
                             "output_schema": genome.output_schema}, ensure_ascii=False),
            timeout_seconds=min(envelope.budget.max_runtime_seconds or 60, 1800),
            evidence_texts=evidence_texts, context=dict(envelope.context))
        response = self.provider.generate(request)                 # ONE model call, no retries here
        execution.latency_ms = response.latency_ms
        execution.model = response.model or execution.model

        # 7. provider failure -> FAILED (never a fabricated result)
        if not response.ok:
            execution.status = AgentStatus.RUNNING
            self.registry.advance(genome.agent_id, AgentStatus.FAILED, actor=CORE_ACTOR,
                                  reason=f"provider {response.status.value}")
            execution.status = AgentStatus.FAILED
            execution.failure_reason = f"PROVIDER_{response.status.value}: {response.error}"[:300]
            execution.finished_at = _utc_iso()
            execution.provenance.append(f"provider_status:{response.status.value}")
            return execution

        # 8. structured output validation against the DECLARED schema subset
        try:
            parsed = json.loads(response.text)
        except Exception as exc:
            return self._fail(genome, execution, "MALFORMED_MODEL_OUTPUT", str(exc))
        if not isinstance(parsed, dict):
            return self._fail(genome, execution, "MALFORMED_MODEL_OUTPUT", "top-level JSON is not an object")
        problems = validate_structured_result(genome.output_schema or {}, parsed)
        if problems:
            return self._fail(genome, execution, "OUTPUT_SCHEMA_VIOLATION", "; ".join(problems[:3]))

        # 9. prompt-injection / authority leakage guard (a model may never grant itself authority)
        try:
            genome.assert_no_authority_escalation({k: parsed.get(k) for k in
                                                   ("authority_scope", "canonical_status", "execution_mode",
                                                    "promote", "release", "approved", "owner")
                                                   if k in parsed})
        except AgentContractError as exc:
            return self._fail(genome, execution, "PROMPT_INJECTION_REJECTED", exc.reason_code)

        # 10. ReturnPackage — ALWAYS a CANDIDATE with real evidence refs and provenance
        return_package = ReturnPackage(
            return_id=f"RET-{execution.execution_id}", work_id=genome.work_id,
            problem_id=genome.problem_id, task_id=genome.task_id, agent_id=genome.agent_id,
            execution_id=execution.execution_id, status=ReturnStatus.RESULT, result=parsed,
            predicates=list(genome.predicates),
            evidence_refs=list(envelope.authorized_evidence_ids) if evidence_texts else [],
            uncertainty=genome.uncertainty, model_used=execution.model,
            provenance=[f"agent:{genome.agent_id}", f"execution:{execution.execution_id}",
                        f"provider:{self.provider.name}", f"model:{execution.model}",
                        f"envelope:{envelope.envelope_id}"] +
                       [f"evidence:{eid}" for eid in (envelope.authorized_evidence_ids if evidence_texts else [])])
        return_package.validate_against(genome)                     # evidence+provenance enforced
        execution.return_package = return_package
        execution.evidence_ids = list(return_package.evidence_refs)

        # 11. RETURNED (the agent reports its own outcome) -> VALIDATION_REQUIRED (Core decides)
        self.registry.advance(genome.agent_id, AgentStatus.RETURNED, actor=agent_actor(genome.agent_id),
                              reason="execution returned a candidate package")
        self.registry.advance(genome.agent_id, AgentStatus.VALIDATION_REQUIRED, actor=CORE_ACTOR,
                              reason="awaiting Python/Core validation (never self-validated)")
        execution.status = AgentStatus.VALIDATION_REQUIRED
        execution.finished_at = _utc_iso()
        return execution

    def _fail(self, genome: AgentGenome, execution: AgentExecutionRecord, reason_code: str,
              detail: str = "") -> AgentExecutionRecord:
        execution.status = AgentStatus.FAILED
        execution.failure_reason = f"{reason_code}: {detail}"[:300] if detail else reason_code
        execution.finished_at = _utc_iso()
        execution.provenance.append(f"FAIL_CLOSED {reason_code}")
        try:
            self.registry.advance(genome.agent_id, AgentStatus.FAILED, actor=CORE_ACTOR,
                                  reason=reason_code)
        except AgentContractError:
            pass
        return execution


def _utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
