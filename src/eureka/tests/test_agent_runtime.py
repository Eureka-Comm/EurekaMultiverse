"""EUREKA 5.1 — LOOP 3 tests: FIRST REAL EMERGENT AGENT (AgentRuntime, fail-closed).

Mandated coverage (Harness LOOP 3): real request -> real model execution -> real ReturnPackage ->
evidence -> provenance -> validation -> Core; fail closed on model unavailable, timeout, malformed
output, missing evidence, invalid schema and policy violation; never fabricate a result. Adversarial:
prompt injection, fake evidence, fake validation, fake agent_id, fake authority, hallucinated result,
malformed response, timeout, duplicate execution, restart.

The REAL model call is authorised separately (one call) and is NOT part of this suite: here the
provider is the deterministic LOCAL double, so the suite is reproducible and free.
"""
import pathlib
import tempfile

import pytest

from src.eureka.universe.agent_genome import (AgentContractError, AgentGenome, AgentIdentity,
                                             AgentNetworkState, AgentStatus, CognitiveFamily,
                                             NetworkRole, ResourceBudget, ReturnStatus, TaskEnvelope)
from src.eureka.universe.agent_registry import CORE_ACTOR, AgentRegistry
from src.eureka.universe.agent_runtime import (DeterministicModelProvider, ModelRequest, ModelResponse,
                                              AgentRuntime, validate_structured_result)
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.cognitive_provider import ProviderResult
from src.eureka.universe.problem_model import ProblemModel
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-EMERGENT-1"
PROBLEM = "PROB-EMERGENT-1"
SCHEMA = {"type": "object", "required": ["lead_time_days"],
          "properties": {"lead_time_days": {"type": "number"}, "rationale": {"type": "string"}}}
EVIDENCE = {"EVI-1": "Supplier A lead times: 10, 12, 14 days."}


def _canonical() -> CanonicalWorkState:
    canonical = CanonicalWorkState(work=EurekaWork(work_id=WORK, title="t", user_intent="u",
                                                   task_category="c", problem_statement="p"))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=PROBLEM)
    return canonical


def _genome(**overrides) -> AgentGenome:
    data = dict(identity=AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                       network_role=NetworkRole.SEGREGATOR,
                                       predicate="LeadTime", context="Europe"),
                work_id=WORK, problem_id=PROBLEM, task_id="TASK-LEADTIME-EUROPE",
                objective="Predict supplier lead time", predicates=["LeadTime"],
                tools=["acfl.evaluate"], evidence_requirements=["series"],
                output_schema=SCHEMA, resource_budget=ResourceBudget(max_model_calls=1))
    data.update(overrides)
    return AgentGenome(**data)


def _envelope(genome: AgentGenome, **overrides) -> TaskEnvelope:
    data = dict(envelope_id="ENV-1", work_id=genome.work_id, problem_id=genome.problem_id,
                task_id=genome.task_id, agent_id=genome.agent_id, genome_hash=genome.hash(),
                authorized_inputs=["PROBLEM"], authorized_evidence_ids=["EVI-1"],
                allowed_tools=["acfl.evaluate"], budget=ResourceBudget(max_model_calls=1))
    data.update(overrides)
    return TaskEnvelope(**data)


def _env(mode="OK", *, payload=None, resolver=None, allowed_models=None):
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    genome = _genome()
    registry.register(genome)
    registry.advance(genome.agent_id, AgentStatus.READY, actor=CORE_ACTOR)
    provider = DeterministicModelProvider(mode=mode, payload=payload)
    evidence = resolver if resolver is not None else (lambda eid, wid: EVIDENCE.get(eid))
    runtime = AgentRuntime(registry, provider, evidence_resolver=evidence, allowed_models=allowed_models)
    return runtime, registry, genome, provider, canonical


# ============================================================================================= #
# happy path (real flow, deterministic provider)
# ============================================================================================= #
def test_execution_flow_produces_a_candidate_return_package_with_evidence_and_provenance():
    runtime, registry, genome, provider, canonical = _env()
    execution = runtime.execute(genome, _envelope(genome))

    assert execution.status is AgentStatus.VALIDATION_REQUIRED          # never VALIDATED by the agent
    assert len(provider.calls) == 1                                     # exactly ONE model call
    rp = execution.return_package
    assert rp is not None and rp.validation_status == "CANDIDATE"
    assert rp.result["lead_time_days"] == 12
    assert rp.evidence_refs == ["EVI-1"]                                # real authorized evidence
    assert any("provider:DeterministicModelProvider" in p for p in rp.provenance)
    assert any(p.startswith("evidence:EVI-1") for p in rp.provenance)
    assert execution.evidence_ids == ["EVI-1"]
    assert execution.model and execution.latency_ms >= 0 and execution.started_at and execution.finished_at

    # the agent's lifecycle is governed and the execution is persisted in the CANONICAL container
    record = registry.resolve(genome.agent_id)
    assert record.status is AgentStatus.VALIDATION_REQUIRED
    assert [e.to_status for e in record.history] == [AgentStatus.CREATED, AgentStatus.READY,
                                                     AgentStatus.RUNNING, AgentStatus.RETURNED,
                                                     AgentStatus.VALIDATION_REQUIRED]
    assert canonical.agent_network.executions[0] is execution


def test_return_package_evidence_refs_are_never_invented():
    runtime, registry, genome, provider, _ = _env()
    execution = runtime.execute(genome, _envelope(genome))
    authorized = {"EVI-1"}
    assert set(execution.return_package.evidence_refs) <= authorized


# ============================================================================================= #
# fail-closed: provider failure modes (never fabricate)
# ============================================================================================= #
@pytest.mark.parametrize("mode,expected", [
    ("UNAVAILABLE", "PROVIDER_UNAVAILABLE"),
    ("TIMEOUT", "PROVIDER_TIMEOUT"),
    ("MALFORMED", "MALFORMED_MODEL_OUTPUT"),
    ("HALLUCINATED", "OUTPUT_SCHEMA_VIOLATION"),
    ("PROMPT_INJECTION", "PROMPT_INJECTION_REJECTED"),
])
def test_provider_failures_fail_closed_without_a_result(mode, expected):
    runtime, registry, genome, provider, _ = _env(mode=mode)
    execution = runtime.execute(genome, _envelope(genome))
    assert execution.status is AgentStatus.FAILED
    assert execution.failure_reason.startswith(expected)
    assert execution.return_package is None                    # NO fabricated result
    assert registry.resolve(genome.agent_id).status is AgentStatus.FAILED


def test_prompt_injection_cannot_grant_authority():
    runtime, registry, genome, provider, _ = _env(mode="PROMPT_INJECTION")
    execution = runtime.execute(genome, _envelope(genome))
    assert execution.status is AgentStatus.FAILED
    record = registry.resolve(genome.agent_id)
    assert record.genome.authority_scope == "PROPOSER"          # authority unchanged
    assert record.genome.identity.cognitive_family is CognitiveFamily.PREDICTOR
    with pytest.raises(AgentContractError):
        registry.update_genome(genome.agent_id, {"authority_scope": "AUTHORITY"})


def test_missing_required_evidence_blocks_instead_of_answering():
    runtime, registry, genome, provider, _ = _env(resolver=lambda eid, wid: None)
    execution = runtime.execute(genome, _envelope(genome))
    assert execution.status is AgentStatus.BLOCKED
    assert execution.failure_reason.startswith("EVIDENCE_UNAVAILABLE")
    assert provider.calls == []                                 # the model was never asked
    assert execution.return_package is None


def test_no_authorized_evidence_returns_insufficient_evidence():
    runtime, registry, genome, provider, _ = _env()
    execution = runtime.execute(genome, _envelope(genome, authorized_evidence_ids=[]))
    assert execution.status is AgentStatus.BLOCKED
    assert execution.failure_reason.startswith("EVIDENCE_REQUIRED_MISSING")
    assert execution.return_package is not None
    assert execution.return_package.status is ReturnStatus.INSUFFICIENT_EVIDENCE
    assert provider.calls == []


# ============================================================================================= #
# fail-closed: identity / scope / lifecycle / budget / model policy
# ============================================================================================= #
def test_fake_agent_id_envelope_is_rejected():
    runtime, registry, genome, provider, _ = _env()
    other = _genome(identity=AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                           network_role=NetworkRole.SEGREGATOR,
                                           predicate="SupplierReliability", context="Europe"))
    # an envelope that names ANOTHER agent is rejected at execution time (the envelope alone cannot
    # know the genome, so the guard lives where both are known — fail closed, no provider call).
    forged = _envelope(genome).model_copy(deep=True)
    object.__setattr__(forged, "agent_id", other.agent_id)
    execution = runtime.execute(genome, forged)
    assert execution.status is AgentStatus.BLOCKED
    assert execution.failure_reason.startswith("ENVELOPE_AGENT_MISMATCH")
    assert provider.calls == []


def test_cross_work_envelope_is_rejected():
    runtime, registry, genome, provider, _ = _env()
    envelope = _envelope(genome)
    forged = envelope.model_copy(deep=True)
    object.__setattr__(forged, "work_id", "WORK-OTHER")
    execution = runtime.execute(genome, forged)
    assert execution.status is AgentStatus.BLOCKED
    assert execution.failure_reason.startswith("CROSS_WORK_CONTAMINATION")
    assert provider.calls == []


def test_stale_genome_is_rejected():
    runtime, registry, genome, provider, _ = _env()
    stale = _genome(objective="a DIFFERENT objective (stale genome)")
    execution = runtime.execute(stale, _envelope(stale, genome_hash=stale.hash()))
    assert execution.status is AgentStatus.BLOCKED
    assert execution.failure_reason.startswith("AGENT_NOT_REGISTERED_OR_STALE")
    assert provider.calls == []


def test_execution_requires_a_ready_agent_illegal_lifecycle_fails_closed():
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    genome = _genome()
    registry.register(genome)                                   # CREATED, not READY
    provider = DeterministicModelProvider()
    runtime = AgentRuntime(registry, provider, evidence_resolver=lambda eid, wid: EVIDENCE.get(eid))
    execution = runtime.execute(genome, _envelope(genome))
    assert execution.status is AgentStatus.BLOCKED
    assert execution.failure_reason.startswith("ILLEGAL_LIFECYCLE_TRANSITION")
    assert provider.calls == []


def test_budget_and_model_policy_are_enforced():
    runtime, registry, genome, provider, _ = _env()
    zero_budget = _envelope(genome, budget=ResourceBudget(max_model_calls=0))
    execution = runtime.execute(genome, zero_budget)
    assert execution.status is AgentStatus.BLOCKED
    assert execution.failure_reason.startswith("BUDGET_MODEL_CALLS_EXHAUSTED")

    runtime2, registry2, genome2, provider2, _ = _env(allowed_models=["some-other-model"])
    execution2 = runtime2.execute(genome2, _envelope(genome2))
    assert execution2.status is AgentStatus.BLOCKED
    assert execution2.failure_reason.startswith("UNAUTHORIZED_MODEL")
    assert provider2.calls == []


# ============================================================================================= #
# duplicate execution · restart
# ============================================================================================= #
def test_duplicate_execution_is_idempotent_and_calls_the_model_once():
    runtime, registry, genome, provider, canonical = _env()
    first = runtime.execute(genome, _envelope(genome))
    second = runtime.execute(genome, _envelope(genome))          # same agent/task/attempt
    assert second is first
    assert len(provider.calls) == 1
    assert len(canonical.agent_network.executions) == 1


def test_restart_recovers_the_execution_and_refuses_to_duplicate(tmp_path):
    runtime, registry, genome, provider, canonical = _env()
    first = runtime.execute(genome, _envelope(genome))
    store = WorkStore(str(tmp_path / "works"))
    store[WORK] = canonical                                     # persisted by the EXISTING authority

    reloaded = WorkStore(str(tmp_path / "works"))[WORK]          # restart
    registry2 = AgentRegistry.rebuild_from(reloaded)
    provider2 = DeterministicModelProvider()
    runtime2 = AgentRuntime(registry2, provider2, evidence_resolver=lambda eid, wid: EVIDENCE.get(eid))
    again = runtime2.execute(genome, _envelope(genome))
    assert again.execution_id == first.execution_id              # recovered, not re-executed
    assert provider2.calls == []
    assert reloaded.agent_network.executions[0].return_package is not None


# ============================================================================================= #
# output validation · invariants
# ============================================================================================= #
def test_structured_output_validation_subset():
    assert validate_structured_result(SCHEMA, {"lead_time_days": 3}) == []
    assert validate_structured_result(SCHEMA, {}) == ["$.lead_time_days: required property missing"]
    assert validate_structured_result(SCHEMA, {"lead_time_days": "many"}) == [
        "$.lead_time_days: expected number, got str"]
    assert validate_structured_result({}, {"anything": 1}) == []      # no schema: nothing to enforce
    nested = {"type": "object", "properties": {"items": {"type": "array",
                                                         "items": {"type": "object",
                                                                   "required": ["id"],
                                                                   "properties": {"id": {"type": "string"}}}}}}
    assert validate_structured_result(nested, {"items": [{"id": "a"}, {"nope": 1}]}) == [
        "$.items[1].id: required property missing"]


def test_runtime_module_is_not_a_store_and_the_double_never_reaches_production():
    root = pathlib.Path(__file__).resolve().parents[1]
    text = (root / "universe" / "agent_runtime.py").read_text(encoding="utf-8")
    assert "open(" not in text, "the runtime must not write files (OllamaProvider traces aside)"
    import src.eureka.universe.agent_runtime as mod
    classes = [n for n, o in vars(mod).items() if isinstance(o, type) and o.__module__ == mod.__name__]
    assert [n for n in classes if n.endswith(("Store", "Database", "Repository"))] == []
    # the deterministic double is a TEST/LOCAL surface only: the live server must never reference it
    server_src = (root / "universe" / "server.py").read_text(encoding="utf-8")
    assert "DeterministicModelProvider" not in server_src
    assert "agent_runtime" not in server_src
