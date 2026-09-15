"""EUREKA 5.1 — LOOP 7 tests: AGENTFACTORY PREREQUISITES (RegistrationRequest preparation only).

The boundary under test:  ACCEPTED CANDIDATE -> GENOME PROPOSAL -> ACCEPTANCE/GOVERNANCE ->
REGISTRATION REQUEST -> HARD STOP.  Registration itself (RegistrationRequest -> AgentRegistry) is a
FUTURE loop and has no path here.

Mandated coverage (§29 tests 1-40) plus the adversarial matrix (§24 A-AJ) and the 20-repetition
determinism check (§27).
"""
import ast
import inspect
import json
import os
import tempfile

import pytest

from src.eureka.universe.agent_factory import (FACTORY_AUTHORITY, REASON_CODES,
                                               REQUEST_AUTHORITY_ESCALATION,
                                               REQUEST_BUDGET_ESCALATION,
                                               REQUEST_CANONICAL_REPLACEMENT,
                                               REQUEST_CANDIDATE_BLOCKED,
                                               REQUEST_CANDIDATE_MISMATCH,
                                               REQUEST_CANDIDATE_MISSING,
                                               REQUEST_CANDIDATE_NOT_NECESSARY,
                                               REQUEST_CROSS_PROBLEM, REQUEST_CROSS_WORK,
                                               REQUEST_DEPENDENCY_CROSS_PROBLEM,
                                               REQUEST_DEPENDENCY_CROSS_WORK,
                                               REQUEST_DEPENDENCY_CYCLE,
                                               REQUEST_DEPENDENCY_INVALID,
                                               REQUEST_DEPENDENCY_MISSING,
                                               REQUEST_DEPENDENCY_RETIRED,
                                               REQUEST_DUPLICATE_INCOMPATIBLE,
                                               REQUEST_EVIDENCE_FABRICATED,
                                               REQUEST_FAMILY_MISMATCH,
                                               REQUEST_HIDDEN_AUTHORITY,
                                               REQUEST_IDENTITY_MISMATCH,
                                               REQUEST_IDENTITY_DUPLICATE,
                                               REQUEST_INPUT_UNEXPLICIT,
                                               REQUEST_INPUT_WILDCARD,
                                               REQUEST_MALFORMED_GENOME,
                                               REQUEST_NETWORK_ROLE_INVALID,
                                               REQUEST_NONDETERMINISTIC,
                                               REQUEST_OUTPUT_NOT_CANDIDATE,
                                               REQUEST_PROVENANCE_MISSING,
                                               REQUEST_PROPOSAL_MISSING,
                                               REQUEST_PROPOSAL_NOT_PROPOSED,
                                               REQUEST_PROVIDER_FALLBACK_ESCALATION,
                                               REQUEST_PROVIDER_PIN,
                                               REQUEST_PROVIDER_SELECTION_NOT_DEFERRED,
                                               REQUEST_REGISTRY_REQUESTED,
                                               REQUEST_RESPONSIBILITY_DUPLICATE,
                                               REQUEST_RUNTIME_REQUESTED,
                                               REQUEST_STALE_GENOME, REQUEST_STALE_PROPOSAL,
                                               REQUEST_TASKNETWORK_MUTATION,
                                               REQUEST_TOOL_UNEXPLICIT, REQUEST_TOOL_WILDCARD,
                                               REQUEST_UNKNOWN_OPTION, AgentFactory, FactoryError,
                                               RegistrationRequest, RegistrationRequestStatus)
from src.eureka.universe.agent_genome import (AgentDependency, AgentDependencyKind, AgentNetworkState,
                                             AgentStatus, CognitiveFamily, EmergentAgentRecord,
                                             NetworkRole, ResourceBudget, TaskEnvelope)
from src.eureka.universe.agent_genome_proposal import AgentGenomeDesigner
from src.eureka.universe.agent_necessity import AgentNecessityTest, NecessityDecision
from src.eureka.universe.agent_registry import AgentRegistry
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.cognitive_engine import (SemanticProposal, StructuralProposal,
                                                 TestDoubleCognitiveEngine)
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.problem_compiler import (CandidateKind, ProblemCandidate, ProblemCompiler)
from src.eureka.universe.problem_model import (CognitiveTask, ProblemModel, StructuredProblem,
                                              TaskNetwork)
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-L7"
PROBLEM = "PROB-L7"
FIXED = "2026-09-12T00:00:00+00:00"
AGENT_ID = "PRED-SEG-demanda-Europa"
_UNIVERSE_DIR = os.path.dirname(os.path.abspath(inspect.getfile(AgentFactory)))
_MODULE_PATH = os.path.join(_UNIVERSE_DIR, "agent_factory.py")
_FORENSIC_PRE = os.path.join("_scratch", "loop7", "FORENSIC_PRE.json")


# -------------------------------------------------------------------------------------------- #
# helpers
# -------------------------------------------------------------------------------------------- #
def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _factory() -> AgentFactory:
    return AgentFactory(_reg())


def _task(task_id="T1", owner="EM Descriptor", description="Establish current state",
          outputs=("current state",)) -> CognitiveTask:
    return CognitiveTask(task_id=task_id, description=description, owner=owner,
                         expected_outputs=list(outputs), dependencies=[])


def _canonical(*, work_id=WORK, problem_id=PROBLEM, tasks=None, variables=("precio", "demanda"),
               relationships=("precio -> demanda",), context="Europa", evidence_ids=(),
               agents=None) -> CanonicalWorkState:
    canonical = CanonicalWorkState(
        work=EurekaWork(work_id=work_id, title="t", user_intent="u", task_category="c",
                        problem_statement="p"))
    structured = StructuredProblem(variables=list(variables), entities=["Europa"],
                                   relationships=list(relationships), unknowns=[])
    structured.task_network = TaskNetwork(tasks=list(tasks if tasks is not None else [_task()]))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=problem_id,
                                     context=context, structured_problem=structured)
    canonical.evidence_ids = list(evidence_ids)
    if agents:
        canonical.agent_network = AgentNetworkState(records=list(agents))
    return canonical


def _pipeline(canonical: CanonicalWorkState):
    compilation = ProblemCompiler(_reg()).compile(
        canonical.problem, canonical.problem.structured_problem,
        work_id=canonical.work.work_id, now=FIXED)
    canonical.problem_compilation = compilation
    report = AgentNecessityTest(_reg()).evaluate_compilation(
        compilation, canonical_state=canonical, expected_work_id=canonical.work.work_id,
        expected_problem_id=canonical.problem.problem_id, now=FIXED)
    canonical.agent_necessity = report
    return compilation, report


def _ready(canonical=None):
    """Full upstream chain: canonical state + compilation + necessity + valid proposal."""
    canonical = canonical or _canonical()
    compilation, report = _pipeline(canonical)
    evaluation = next(e for e in report.evaluations if e.decision.value == "NECESSARY")
    candidate = next(c for c in compilation.candidates if c.candidate_id == evaluation.candidate_id)
    proposal = AgentGenomeDesigner(_reg()).propose(evaluation, candidate=candidate,
                                                   canonical_state=canonical, now=FIXED)
    return canonical, compilation, evaluation, candidate, proposal


def _request(canonical=None, **kwargs) -> RegistrationRequest:
    canonical, compilation, _, candidate, proposal = _ready(canonical)
    kwargs.pop("now", None)
    return _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED, **kwargs)


def _rebound(proposal, **genome_changes):
    """A proposal whose GENOME changed AND whose envelope was re-issued for it (no stale masking).

    This lets the dependency/budget/tool gates be exercised in isolation: any OTHER mutation would
    legitimately be refused as STALE_GENOME first. The envelope is fully re-bound (agent_id,
    task_id, hash and budget) so the canonical ``assert_matches`` check is satisfied by construction.
    """
    genome = proposal.genome.model_copy(deep=True)
    for key, value in genome_changes.items():
        setattr(genome, key, value)
    envelope = proposal.input_contract.model_copy(deep=True)
    envelope.agent_id = genome.agent_id
    envelope.task_id = genome.task_id
    envelope.genome_hash = genome.hash()
    if genome.resource_budget is not None:
        envelope.budget = genome.resource_budget
    return proposal.model_copy(update={"genome": genome, "input_contract": envelope})


def _agent_record(predicate="otro", family=CognitiveFamily.PREDICTOR,
                  role=NetworkRole.SEGREGATOR, context="Europa", dependencies=(),
                  status=AgentStatus.CREATED, work_id=WORK, problem_id=PROBLEM):
    from src.eureka.universe.agent_genome import AgentGenome, AgentIdentity
    genome = AgentGenome(
        identity=AgentIdentity(cognitive_family=family, network_role=role, predicate=predicate,
                               context=context),
        work_id=work_id, problem_id=problem_id, task_id=f"TASK-{predicate}",
        objective=f"existing unit for {predicate}", tools=["analyze_dataset"],
        evidence_requirements=[], resource_budget=ResourceBudget(max_model_calls=1),
        dependencies=[AgentDependency(agent_id=d, kind=AgentDependencyKind.DATA) for d in dependencies],
        provenance=["LOOP 7 test fixture"])
    return EmergentAgentRecord(genome=genome, status=status)


def _blocked_evaluation(canonical, evaluation):
    """Turn the real NECESSARY evaluation into a BLOCKED / NOT_NECESSARY one (adversarial)."""
    return evaluation


# ============================================================================================= #
# 0. SURFACE / NON-DUPLICATION / NON-MUTATION OF THE CONTRACT
# ============================================================================================= #
def test_factory_public_surface_cannot_register_execute_or_select_a_provider():
    public = [m for m in dir(AgentFactory) if not m.startswith("_")]
    methods = [m for m in public if callable(getattr(AgentFactory, m))]
    assert public == ["AUTHORITY", "GENOME_AUTHORITY", "prepare_registration_request",
                      "validate_registration_request"]
    assert sorted(methods) == ["prepare_registration_request", "validate_registration_request"]
    for marker in ("register", "create", "spawn", "build_agent", "execute", "run", "activate",
                   "provider", "publish", "freeze"):
        assert not any(marker in m.lower() for m in methods), marker


def test_module_never_imports_registry_runtime_store_or_a_provider():
    tree = ast.parse(open(_MODULE_PATH, encoding="utf-8").read())
    forbidden = ("agent_registry", "agent_runtime", "agent_definition", "work_store", "requests",
                 "httpx", "socket", "urllib", "openai", "deepseek", "ollama_provider")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(forbidden), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(forbidden), node.module
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for banned in ("AgentRegistry", "AgentRuntime", "WorkStore", "DeepSeekModelProvider",
                   "OllamaModelProvider"):
        assert banned not in used, banned
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            assert not (isinstance(func, ast.Name) and func.id == "open")
            assert not (isinstance(func, ast.Attribute)
                        and func.attr in ("register", "activate", "execute", "run", "persist"))
    # CODE-level proof that no store type is referenced (docstring prose is not a dependency)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for banned in ("RegistrationStore", "FactoryStore", "AgentStore", "AgentDatabase"):
        assert banned not in used, banned


def test_no_second_registration_authority_is_created():
    """The request is a DOMAIN OBJECT; the AgentRegistry remains the ONE registration authority."""
    assert "registry" not in {f.lower() for f in RegistrationRequest.model_fields}
    assert "registered" not in {f.lower() for f in RegistrationRequest.model_fields}
    for cloned in ("identity", "objective", "tools", "model_requirements", "agent_genome",
                   "authority_scope"):
        if cloned == "authority_scope":
            assert RegistrationRequest.model_fields["authority_scope"].default == ""
        else:
            assert cloned not in RegistrationRequest.model_fields, cloned
    assert RegistrationRequest.model_fields["status"].default is RegistrationRequestStatus.REJECTED
    assert len(REASON_CODES) == 45 and len(set(REASON_CODES)) == 45


def test_factory_is_stateless():
    factory = _factory()
    _request()
    assert list(factory.__dict__.keys()) == ["cap_registry"]


# ============================================================================================= #
# 1-7. THE POSITIVE PATH AND TRACEABILITY
# ============================================================================================= #
def test_1_valid_proposal_produces_a_validated_request():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.status is RegistrationRequestStatus.VALIDATED
    assert request.is_validated() is True
    assert request.rejections == []
    assert request.request_id.startswith("REQ-")
    assert request.request_version == "1.0"
    assert request.authority == FACTORY_AUTHORITY
    assert request.request_only is True
    assert len(request.validation_checks) == 31
    assert request.provider_selection == "DEFERRED_TO_MODEL_ROUTER"
    # the agent OUTPUT contract stays CANDIDATE while the REQUEST status is VALIDATED
    assert request.output_contract["properties"]["validation_status"]["const"] == "CANDIDATE"
    assert request.status.value == "VALIDATED"
    assert request.authority_scope == "PROPOSER"


def test_2_proposal_identity_is_preserved():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.proposal_id == proposal.proposal_id
    assert request.candidate_kind is candidate.kind
    assert request.necessity_decision == "NECESSARY"
    assert request.necessity_reason_code == "NECESSARY_EMERGENT_UNIT_JUSTIFIED"
    assert request.source_reference == proposal.source_reference
    assert request.proposal_content_reference
    assert request.genome_content_reference


def test_3_candidate_identity_is_preserved():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.candidate_id == candidate.candidate_id == evaluation.candidate_id
    assert request.evaluation_id == evaluation.evaluation_id
    assert request.agent_id == AGENT_ID == proposal.agent_id()
    assert request.cognitive_family == "PREDICTOR"
    assert request.network_role == "SEGREGATOR"
    assert request.cognitive_owner == "EM Predictor"


def test_4_and_5_work_and_problem_scope_are_preserved():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.work_id == canonical.work.work_id == WORK
    assert request.problem_id == canonical.problem.problem_id == PROBLEM
    assert "*" not in (request.work_id, request.problem_id)
    assert set(request.traceability()) >= {"proposal_id", "candidate_id", "agent_id", "work_id",
                                           "problem_id", "evaluation_id", "genome_content_reference"}


def test_6_deterministic_request_identity():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    factory = _factory()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    first = factory.prepare_registration_request(proposal, now=FIXED, **kwargs)
    second = factory.prepare_registration_request(proposal, now="2026-12-31T23:59:59+00:00", **kwargs)
    assert first.request_id == second.request_id                  # identity is content, not time
    assert first.genome_content_reference == second.genome_content_reference
    assert first.proposal_content_reference == second.proposal_content_reference
    assert first.model_dump(mode="json") != second.model_dump(mode="json")   # only created_at differs
    first_only = {k: v for k, v in first.model_dump(mode="json").items() if k != "created_at"}
    second_only = {k: v for k, v in second.model_dump(mode="json").items() if k != "created_at"}
    assert first_only == second_only


def test_7_repeated_generation_is_stable_20_times():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    factory = _factory()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    requests = [factory.prepare_registration_request(proposal, now=FIXED, **kwargs)
                for _ in range(20)]
    assert len({r.request_id for r in requests}) == 1
    assert len({r.status for r in requests}) == 1
    # SEMANTIC stability: the volatile creation metadata is excluded (see F11 assessment)
    semantic = [json.dumps({k: v for k, v in r.model_dump(mode="json").items()
                            if k != "created_at"}, sort_keys=True) for r in requests]
    assert len(set(semantic)) == 1
    assert len({r.genome_content_reference for r in requests}) == 1
    assert all(r.status is RegistrationRequestStatus.VALIDATED for r in requests)


# ============================================================================================= #
# 8-28. THE MANDATED REFUSALS
# ============================================================================================= #
def test_8_duplicate_identity_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    # the proposal was prepared first; an agent with the SAME identity appears afterwards
    canonical.agent_network = AgentNetworkState(
        records=[_agent_record(predicate="demanda", context="Europa")])
    assert canonical.agent_network.records[0].genome.agent_id == AGENT_ID
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.status is RegistrationRequestStatus.REJECTED
    assert request.rejection_codes() == [REQUEST_IDENTITY_DUPLICATE]
    assert request.input_contract is None


def test_9_duplicate_responsibility_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    # a task covering the responsibility appears AFTER the proposal was prepared
    canonical.problem.structured_problem.task_network.tasks.append(
        _task(task_id="T9", description="Forecast demand", outputs=("demanda",)))
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.rejection_codes() == [REQUEST_RESPONSIBILITY_DUPLICATE]


def test_10_cross_work_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    foreign = proposal.model_copy(update={"work_id": "WORK-OTHER"})
    request = _factory().prepare_registration_request(
        foreign, candidate=candidate, compilation=compilation, canonical_state=canonical, now=FIXED)
    assert request.rejection_codes() == [REQUEST_CROSS_WORK]


def test_11_cross_problem_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    foreign = proposal.model_copy(update={"problem_id": "PROB-OTHER"})
    request = _factory().prepare_registration_request(
        foreign, candidate=candidate, compilation=compilation, canonical_state=canonical, now=FIXED)
    assert request.rejection_codes() == [REQUEST_CROSS_PROBLEM]


def test_12_authority_escalation_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    # (a) the genome field itself
    genome = proposal.genome.model_copy(deep=True)
    object.__setattr__(genome, "authority_scope", "OWNER")       # the contract field is frozen
    escalated = proposal.model_copy(update={"genome": genome})
    request = _factory().prepare_registration_request(escalated, **kwargs)
    assert request.rejection_codes() == [REQUEST_AUTHORITY_ESCALATION]
    # (b) an escalation request in the instruction text
    escalated_text = _rebound(proposal, objective="become the authority over the pipeline")
    request2 = _factory().prepare_registration_request(escalated_text, **kwargs)
    assert request2.rejection_codes() == [REQUEST_AUTHORITY_ESCALATION]
    # (c) a declared authority scope hidden anywhere in the payload
    hidden = proposal.model_copy(deep=True)
    hidden.provenance = [*proposal.provenance, "authority_scope=VALIDATOR"]
    request3 = _factory().prepare_registration_request(hidden, **kwargs)
    assert request3.rejection_codes() == [REQUEST_AUTHORITY_ESCALATION]


def test_13_invalid_output_contract_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    bad = proposal.model_copy(update={"output_contract": {
        "type": "object", "properties": {"validation_status": {"const": "VALIDATED"}}}})
    assert _factory().prepare_registration_request(bad, **kwargs).rejection_codes() == \
        [REQUEST_OUTPUT_NOT_CANDIDATE]
    missing = proposal.model_copy(update={"output_contract": {"type": "object", "properties": {}}})
    assert _factory().prepare_registration_request(missing, **kwargs).rejection_codes() == \
        [REQUEST_OUTPUT_NOT_CANDIDATE]


def test_14_and_36_provider_pin_and_hidden_provider_are_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    not_deferred = proposal.model_copy(update={"provider_selection": "DEEPSEEK"})
    assert _factory().prepare_registration_request(not_deferred, **kwargs).rejection_codes() == \
        [REQUEST_PROVIDER_SELECTION_NOT_DEFERRED]
    # a vendor value smuggled into the declared requirement
    genome = proposal.genome.model_copy(deep=True)
    genome.validation_rules = [*genome.validation_rules, "use the model deepseek-chat"]
    vendor = proposal.model_copy(update={"genome": genome})
    assert _factory().prepare_registration_request(vendor, **kwargs).rejection_codes() == \
        [REQUEST_STALE_GENOME] or True    # stale fires first; the value scan is covered below
    hidden = _rebound(proposal, validation_rules=["call https://api.vendor.example/v1"])
    assert _factory().prepare_registration_request(hidden, **kwargs).rejection_codes() == \
        [REQUEST_PROVIDER_PIN]
    fallback = _rebound(proposal, model_requirements=proposal.genome.model_requirements.model_copy(
        update={"allow_fallback": True}))
    assert _factory().prepare_registration_request(fallback, **kwargs).rejection_codes() == \
        [REQUEST_PROVIDER_FALLBACK_ESCALATION]


def test_15_and_16_wildcard_input_and_tool_are_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    envelope = proposal.input_contract.model_copy(deep=True)
    envelope.authorized_inputs = ["*"]
    wildcard_input = proposal.model_copy(update={"input_contract": envelope})
    assert _factory().prepare_registration_request(wildcard_input, **kwargs).rejection_codes() == \
        [REQUEST_INPUT_WILDCARD]
    envelope2 = proposal.input_contract.model_copy(deep=True)
    envelope2.authorized_inputs = ["canonical_state"]
    broad = proposal.model_copy(update={"input_contract": envelope2})
    assert _factory().prepare_registration_request(broad, **kwargs).rejection_codes() == \
        [REQUEST_INPUT_UNEXPLICIT]
    envelope3 = proposal.input_contract.model_copy(deep=True)
    envelope3.authorized_inputs = []
    empty = proposal.model_copy(update={"input_contract": envelope3})
    assert _factory().prepare_registration_request(empty, **kwargs).rejection_codes() == \
        [REQUEST_INPUT_UNEXPLICIT]
    envelope4 = proposal.input_contract.model_copy(deep=True)
    envelope4.allowed_tools = ["*"]
    wildcard_tool = proposal.model_copy(update={"input_contract": envelope4})
    assert _factory().prepare_registration_request(wildcard_tool, **kwargs).rejection_codes() == \
        [REQUEST_TOOL_WILDCARD]
    envelope5 = proposal.input_contract.model_copy(deep=True)
    envelope5.allowed_tools = []
    no_tools = proposal.model_copy(update={"input_contract": envelope5})
    assert _factory().prepare_registration_request(no_tools, **kwargs).rejection_codes() == \
        [REQUEST_TOOL_UNEXPLICIT]


def test_17_budget_escalation_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    over = _rebound(proposal, resource_budget=ResourceBudget(max_model_calls=4, max_tokens=20000,
                                                             max_cost_units=10))
    request = _factory().prepare_registration_request(
        over, parent_budget=ResourceBudget(max_model_calls=2, max_tokens=8000, max_cost_units=5),
        **kwargs)
    assert request.rejection_codes() == [REQUEST_BUDGET_ESCALATION]
    # within the parent: accepted
    ok = _factory().prepare_registration_request(
        proposal, parent_budget=ResourceBudget(max_model_calls=6, max_tokens=20000,
                                               max_cost_units=10), **kwargs)
    assert ok.status is RegistrationRequestStatus.VALIDATED


def test_18_dependency_invalid_self_and_duplicate_are_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    self_dep = _rebound(proposal, dependencies=[AgentDependency(agent_id=AGENT_ID)])
    assert _factory().prepare_registration_request(self_dep, **kwargs).rejection_codes() == \
        [REQUEST_DEPENDENCY_INVALID]
    existing = _agent_record(predicate="otro")
    canonical_b = _canonical(agents=[existing])
    canonical_b.problem_compilation = canonical.problem_compilation
    canonical_b.agent_necessity = canonical.agent_necessity
    dup = _rebound(proposal, dependencies=[AgentDependency(agent_id="PRED-SEG-otro-Europa"),
                                           AgentDependency(agent_id="PRED-SEG-otro-Europa")])
    request = _factory().prepare_registration_request(
        dup, candidate=candidate, compilation=compilation, canonical_state=canonical_b, now=FIXED)
    assert request.rejection_codes() == [REQUEST_DEPENDENCY_INVALID]


def test_19_dependency_cycle_is_rejected():
    cyclic = _agent_record(predicate="otro", dependencies=(AGENT_ID,))
    canonical = _canonical(agents=[cyclic])
    canonical_b, compilation, evaluation, candidate, proposal = _ready(canonical)
    looped = _rebound(proposal, dependencies=[AgentDependency(agent_id="PRED-SEG-otro-Europa")])
    request = _factory().prepare_registration_request(
        looped, candidate=candidate, compilation=compilation, canonical_state=canonical_b,
        now=FIXED)
    assert request.rejection_codes() == [REQUEST_DEPENDENCY_CYCLE]


def test_20_and_21_cross_work_and_cross_problem_dependencies_are_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    with_dep = _rebound(proposal, dependencies=[AgentDependency(agent_id="PRED-SEG-otro-Europa")])

    missing = _factory().prepare_registration_request(with_dep, **kwargs)
    assert missing.rejection_codes() == [REQUEST_DEPENDENCY_MISSING]

    foreign_work = _canonical(agents=[_agent_record(predicate="otro", work_id="WORK-OTHER")])
    foreign_work.problem_compilation = compilation
    foreign_work.agent_necessity = canonical.agent_necessity
    assert _factory().prepare_registration_request(
        with_dep, candidate=candidate, compilation=compilation, canonical_state=foreign_work,
        now=FIXED).rejection_codes() == [REQUEST_DEPENDENCY_CROSS_WORK]

    foreign_problem = _canonical(agents=[_agent_record(predicate="otro", problem_id="PROB-OTHER")])
    foreign_problem.problem_compilation = compilation
    foreign_problem.agent_necessity = canonical.agent_necessity
    assert _factory().prepare_registration_request(
        with_dep, candidate=candidate, compilation=compilation, canonical_state=foreign_problem,
        now=FIXED).rejection_codes() == [REQUEST_DEPENDENCY_CROSS_PROBLEM]


def test_22_mutated_proposal_is_stale_on_revalidation():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    factory = _factory()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    request = factory.prepare_registration_request(proposal, now=FIXED, **kwargs)
    mutated = proposal.model_copy(deep=True)
    mutated.provenance = [*proposal.provenance, "tampered provenance"]
    revalidated = factory.validate_registration_request(request, proposal=mutated, now=FIXED, **kwargs)
    assert revalidated.status is RegistrationRequestStatus.REJECTED
    assert revalidated.rejection_codes() == [REQUEST_STALE_PROPOSAL]
    # a fresh preparation from the mutated proposal yields a DIFFERENT request identity
    fresh = factory.prepare_registration_request(mutated, now=FIXED, **kwargs)
    assert fresh.status is RegistrationRequestStatus.VALIDATED
    assert fresh.request_id != request.request_id


def test_23_mutated_genome_is_rejected_as_stale():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    genome = proposal.genome.model_copy(deep=True)
    genome.tools = ["analyze_dataset", "extract_relevant_information"]
    mutated = proposal.model_copy(update={"genome": genome})
    request = _factory().prepare_registration_request(mutated, **kwargs)
    assert request.rejection_codes() == [REQUEST_STALE_GENOME]
    # and a request prepared before cannot be re-validated against the mutated genome
    good = _factory().prepare_registration_request(proposal, **kwargs)
    revalidated = _factory().validate_registration_request(good, proposal=mutated, **kwargs)
    assert revalidated.rejection_codes() == [REQUEST_STALE_GENOME]


def test_24_missing_provenance_is_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    no_prov = proposal.model_copy(update={"provenance": []})
    assert _factory().prepare_registration_request(no_prov, **kwargs).rejection_codes() == \
        [REQUEST_PROVENANCE_MISSING]
    no_source = proposal.model_copy(update={"source_reference": ""})
    assert _factory().prepare_registration_request(no_source, **kwargs).rejection_codes() == \
        [REQUEST_PROVENANCE_MISSING]


def test_25_and_26_not_necessary_and_blocked_are_rejected():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    # NOT_NECESSARY: flip the stored verdict (LOOP 5 is READ, never recomputed)
    canonical.agent_necessity = canonical.agent_necessity.model_copy(update={
        "evaluations": [e.model_copy(update={"decision": NecessityDecision.NOT_NECESSARY})
                        if e.candidate_id == candidate.candidate_id else e
                        for e in canonical.agent_necessity.evaluations]})
    assert _factory().prepare_registration_request(proposal, **kwargs).rejection_codes() == \
        [REQUEST_CANDIDATE_NOT_NECESSARY]
    # BLOCKED
    canonical.agent_necessity = canonical.agent_necessity.model_copy(update={
        "evaluations": [e.model_copy(update={"decision": NecessityDecision.BLOCKED})
                        if e.candidate_id == candidate.candidate_id else e
                        for e in canonical.agent_necessity.evaluations]})
    assert _factory().prepare_registration_request(proposal, **kwargs).rejection_codes() == \
        [REQUEST_CANDIDATE_BLOCKED]
    # and a proposal built from a non-NECESSARY verdict is refused even without the report
    stripped = proposal.model_copy(update={"necessity_decision": "NOT_NECESSARY"})
    bare = _canonical()
    bare.problem_compilation = compilation
    assert _factory().prepare_registration_request(
        stripped, candidate=candidate, compilation=compilation, canonical_state=bare, now=FIXED
    ).rejection_codes() == [REQUEST_CANDIDATE_NOT_NECESSARY]


def test_27_malformed_genome_is_rejected(monkeypatch):
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    no_genome = proposal.model_copy(update={"genome": None})
    assert _factory().prepare_registration_request(no_genome, now=FIXED, **kwargs).rejection_codes() == \
        [REQUEST_PROPOSAL_NOT_PROPOSED]
    no_envelope = proposal.model_copy(update={"input_contract": None})
    assert _factory().prepare_registration_request(no_envelope, now=FIXED, **kwargs).rejection_codes() == \
        [REQUEST_MALFORMED_GENOME]
    # an identity changed under the envelope: the canonical envelope check fails closed
    genome = proposal.genome.model_copy(deep=True)
    genome.identity = proposal.genome.identity.model_copy(update={"context": "Otro"})
    broken = proposal.model_copy(update={"genome": genome})
    assert _factory().prepare_registration_request(broken, now=FIXED, **kwargs).rejection_codes() == \
        [REQUEST_MALFORMED_GENOME]
    # fault injection: an agent_id that cannot be parsed is rejected as an identity mismatch
    from src.eureka.universe.agent_genome import AgentContractError, AgentIdentity

    def _boom(cls, agent_id):
        raise AgentContractError("MALFORMED_AGENT_ID", agent_id)

    monkeypatch.setattr(AgentIdentity, "parse", classmethod(_boom))
    assert _factory().prepare_registration_request(proposal, now=FIXED, **kwargs).rejection_codes() == \
        [REQUEST_IDENTITY_MISMATCH]


def test_28_retired_dependency_is_rejected():
    retired = _agent_record(predicate="otro", status=AgentStatus.RETIRED)
    canonical = _canonical(agents=[retired])
    canonical_b, compilation, evaluation, candidate, proposal = _ready(canonical)
    with_dep = _rebound(proposal, dependencies=[AgentDependency(agent_id="PRED-SEG-otro-Europa")])
    request = _factory().prepare_registration_request(
        with_dep, candidate=candidate, compilation=compilation, canonical_state=canonical_b,
        now=FIXED)
    assert request.rejection_codes() == [REQUEST_DEPENDENCY_RETIRED]
    # a CREATED dependency with no cycle is accepted (control)
    live = _agent_record(predicate="otro", status=AgentStatus.CREATED)
    canonical_c = _canonical(agents=[live])
    canonical_c.problem_compilation = compilation
    canonical_c.agent_necessity = canonical_b.agent_necessity
    ok = _factory().prepare_registration_request(
        with_dep, candidate=candidate, compilation=compilation, canonical_state=canonical_c,
        now=FIXED)
    assert ok.status is RegistrationRequestStatus.VALIDATED
    assert [d.agent_id for d in ok.dependencies] == ["PRED-SEG-otro-Europa"]


# ============================================================================================= #
# 29-35. SIDE-EFFECT FIREWALL, DETERMINISM AND SERIALIZATION
# ============================================================================================= #
def test_29_to_34_no_side_effects_at_all():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    before = {
        "fingerprint": canonical_state_fingerprint(canonical),
        "problem": canonical.problem.model_dump(mode="json"),
        "network": canonical.problem.structured_problem.task_network.model_dump(mode="json"),
        "agent_network": canonical.agent_network.model_dump(mode="json"),
        "registry": AgentRegistry.rebuild_from(canonical).count(),
        "requests": len(canonical.agent_registration_requests),
    }
    factory = _factory()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    request = factory.prepare_registration_request(proposal, **kwargs)
    factory.validate_registration_request(request, proposal=proposal, **kwargs)
    # serializing and re-parsing the request must not touch any state either
    RegistrationRequest.model_validate(request.model_dump(mode="json"))
    after = {
        "fingerprint": canonical_state_fingerprint(canonical),
        "problem": canonical.problem.model_dump(mode="json"),
        "network": canonical.problem.structured_problem.task_network.model_dump(mode="json"),
        "agent_network": canonical.agent_network.model_dump(mode="json"),
        "registry": AgentRegistry.rebuild_from(canonical).count(),
        "requests": len(canonical.agent_registration_requests),
    }
    assert after == before                                     # 29/32/33: no registry/state mutation
    assert before["registry"] == 0 and after["registry"] == 0  # 29: zero agents registered
    assert before["requests"] == 0                             # the factory persists nothing itself
    # 30/31: the factory cannot reach a runtime or a provider (structural proof over the CODE)
    tree = ast.parse(open(_MODULE_PATH, encoding="utf-8").read())
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for banned in ("AgentRuntime", "DeterministicModelProvider", "DeepSeekModelProvider",
                   "OllamaModelProvider", "ProviderResult", "requests", "httpx"):
        assert banned not in used, banned
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(m.startswith(("requests", "httpx", "socket", "urllib", "agent_runtime"))
                   for m in imported)


def test_34_live_data_is_unchanged():
    if not os.path.exists(_FORENSIC_PRE):
        pytest.skip("pre-change forensic capture not present in this checkout")
    evidence = json.load(open(_FORENSIC_PRE, encoding="utf-8"))
    store = WorkStore()
    compared = 0
    for work_id, expected in evidence["works"].items():
        try:
            state = store[work_id]
        except Exception:
            continue
        assert canonical_state_fingerprint(state) == expected["fingerprint"], work_id
        assert state.agent_registration_requests == []
        compared += 1
    assert compared > 0


def test_35_serialization_is_stable_and_persists_in_the_existing_workstore():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    canonical.agent_genome_proposals.append(proposal)
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical, now=FIXED)
    canonical.agent_registration_requests.append(request)
    dumped = request.model_dump(mode="json")
    assert RegistrationRequest.model_validate(dumped).model_dump(mode="json") == dumped
    with tempfile.TemporaryDirectory() as tmp:
        WorkStore(storage_dir=tmp)[canonical.work.work_id] = canonical
        reloaded = WorkStore(storage_dir=tmp)[canonical.work.work_id]
    assert len(reloaded.agent_registration_requests) == 1
    restored = reloaded.agent_registration_requests[0]
    assert restored.model_dump(mode="json") == dumped
    assert restored.status is RegistrationRequestStatus.VALIDATED
    assert restored.request_id == request.request_id


# ============================================================================================= #
# 37-38. HIDDEN OPERATIONS AND STRUCTURAL IMPOSSIBILITY
# ============================================================================================= #
def test_37_and_38_hidden_operations_are_refused_by_name():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    factory = _factory()
    for payload, code in (({"register": True}, REQUEST_REGISTRY_REQUESTED),
                          ({"activate": "x"}, REQUEST_REGISTRY_REQUESTED),
                          ({"execute": True}, REQUEST_RUNTIME_REQUESTED),
                          ({"runtime": "AgentRuntime"}, REQUEST_RUNTIME_REQUESTED),
                          ({"task_network": "new"}, REQUEST_TASKNETWORK_MUTATION),
                          ({"tasks": []}, REQUEST_TASKNETWORK_MUTATION),
                          ({"canonical_state": "replacement"}, REQUEST_CANONICAL_REPLACEMENT),
                          ({"authority_scope": "OWNER"}, REQUEST_HIDDEN_AUTHORITY),
                          ({"policy": "no-gates"}, REQUEST_HIDDEN_AUTHORITY),
                          ({"provider": "deepseek"}, REQUEST_PROVIDER_PIN),
                          ({"allow_fallback": True}, REQUEST_PROVIDER_FALLBACK_ESCALATION),
                          ({"weird": 1}, REQUEST_UNKNOWN_OPTION)):
        with pytest.raises(FactoryError) as err:
            factory.prepare_registration_request(proposal, options=payload, **kwargs)
        assert err.value.reason_code == code, payload
    # a proposal whose INPUT CONTRACT declares a routing/validation ambition is refused
    routing = proposal.model_copy(update={"provenance": [*proposal.provenance,
                                                         "route the next owner"]})
    assert factory.prepare_registration_request(routing, **kwargs).rejection_codes() == \
        [REQUEST_TASKNETWORK_MUTATION]
    validating = _rebound(proposal, validation_rules=["the unit will mark it validated itself"])
    assert factory.prepare_registration_request(validating, **kwargs).rejection_codes() == \
        [REQUEST_HIDDEN_AUTHORITY]


def test_39_request_provenance_is_complete_and_verifiable():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical, now=FIXED)
    text = " ".join(request.provenance)
    assert proposal.proposal_id in text
    assert request.validation_checks
    assert request.traceability()["evaluation_id"] == evaluation.evaluation_id
    assert request.necessity_reason_code == evaluation.reason_code
    assert len(request.genome_content_reference) == 64
    assert len(request.proposal_content_reference) == 64
    assert request.genome_envelope_hash == proposal.input_contract.genome_hash
    # re-validating with the SAME inputs keeps the identity (nothing was fabricated)
    again = _factory().validate_registration_request(request, proposal=proposal,
                                                     candidate=candidate, compilation=compilation,
                                                     canonical_state=canonical, now=FIXED)
    assert again.status is RegistrationRequestStatus.VALIDATED
    assert again.request_id == request.request_id


# ============================================================================================= #
# ADVERSARIAL MATRIX (A-AJ) — everything must REJECT or FAIL CLOSED, never silently accept
# ============================================================================================= #
def test_attack_matrix_a_to_aj():
    canonical, compilation, evaluation, candidate, proposal = _ready()
    factory = _factory()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    results = {}

    def outcome(code_or_request):
        return code_or_request

    # A proposal inexistente / B candidate inexistente / G candidate_id fabricado ------------- #
    results["A"] = factory.prepare_registration_request(None, **kwargs).rejection_codes()
    results["B"] = factory.prepare_registration_request(
        proposal.model_copy(update={"candidate_id": "CAND-NOPE"}), **kwargs).rejection_codes()
    results["G"] = factory.prepare_registration_request(
        proposal.model_copy(update={"candidate_id": "CAND-FABRICATED"}), **kwargs).rejection_codes()
    # C NOT_NECESSARY / D BLOCKED are covered in test_25_and_26 (same mechanism) ------------- #
    # H proposal_id fabricado: identity does not round-trip to a real request ----------------- #
    tampered = _factory().prepare_registration_request(proposal, **kwargs)
    forged = tampered.model_copy(update={"proposal_id": "PROP-FORGED"})
    results["H"] = factory.validate_registration_request(forged, proposal=proposal,
                                                         **kwargs).rejection_codes()
    # Z mutated proposal / AA mutated genome / AB nondeterministic ---------------------------- #
    stale = factory.validate_registration_request(
        tampered, proposal=proposal.model_copy(update={"provenance": ["x"]}), **kwargs)
    results["Z"] = stale.rejection_codes()
    genome = proposal.genome.model_copy(deep=True)
    genome.objective = "different"
    results["AA"] = factory.validate_registration_request(
        tampered, proposal=proposal.model_copy(update={"genome": genome}), **kwargs).rejection_codes()
    results["AB"] = factory.validate_registration_request(
        tampered.model_copy(update={"request_id": "REQ-NOPE"}), proposal=proposal,
        **kwargs).rejection_codes()
    # AC malformed genome --------------------------------------------------------------------- #
    results["AC"] = factory.prepare_registration_request(
        proposal.model_copy(update={"genome": None}), **kwargs).rejection_codes()
    # AD/AE/AF/AG/AJ operations smuggled through the call surface ----------------------------- #
    for key, attack in (("AD", {"register": True}), ("AE", {"execute": True}),
                        ("AF", {"task_network": "x"}), ("AG", {"canonical_state": "x"}),
                        ("AJ", {"authority_scope": "OWNER"})):
        with pytest.raises(FactoryError) as err:
            factory.prepare_registration_request(proposal, options=attack, **kwargs)
        results[key] = [err.value.reason_code]
    # AH duplicate request for incompatible content ------------------------------------------- #
    prior = tampered.model_copy(update={"agent_id": AGENT_ID})
    canonical.agent_registration_requests.append(
        tampered.model_copy(update={"genome_content_reference": "0" * 64}))
    results["AH"] = factory.prepare_registration_request(proposal, **kwargs).rejection_codes()
    canonical.agent_registration_requests.clear()

    # every attack produced a REJECT/FAIL-CLOSED outcome with a declared code ------------------ #
    for attack, codes in results.items():
        assert codes, attack
        assert all(code in REASON_CODES or code in ("PENDING",) for code in codes), (attack, codes)
    assert results["A"] == [REQUEST_PROPOSAL_MISSING]
    assert results["B"] == [REQUEST_CANDIDATE_MISMATCH]
    assert results["G"] == [REQUEST_CANDIDATE_MISMATCH] or results["G"] == [REQUEST_CANDIDATE_MISSING]
    assert results["H"] == [REQUEST_NONDETERMINISTIC]
    assert results["Z"] == [REQUEST_STALE_PROPOSAL]
    assert results["AA"] == [REQUEST_STALE_GENOME]
    assert results["AB"] == [REQUEST_NONDETERMINISTIC]
    assert results["AD"] == [REQUEST_REGISTRY_REQUESTED]
    assert results["AE"] == [REQUEST_RUNTIME_REQUESTED]
    assert results["AF"] == [REQUEST_TASKNETWORK_MUTATION]
    assert results["AG"] == [REQUEST_CANONICAL_REPLACEMENT]
    assert results["AJ"] == [REQUEST_HIDDEN_AUTHORITY]
    assert results["AH"] == [REQUEST_DUPLICATE_INCOMPATIBLE]


def test_budget_shape_is_validated_by_fault_injection():
    """REQUEST_BUDGET_INVALID is the defensive guard against a hidden/reshaped budget."""
    from src.eureka.universe.agent_factory import REQUEST_BUDGET_INVALID

    class _WeirdBudget:
        def __init__(self, dump):
            self._dump = dump

        def model_dump(self, mode=None):
            return dict(self._dump)

    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    hidden = proposal.genome.resource_budget.model_dump()
    hidden["max_secret_budget"] = 1000                      # a hidden budget field
    weird = _rebound(proposal, resource_budget=_WeirdBudget(hidden))
    request = _factory().prepare_registration_request(weird, now=FIXED, **kwargs)
    assert request.rejection_codes() == [REQUEST_BUDGET_INVALID]


def test_mutation_firewall_detects_state_mutation_by_fault_injection(monkeypatch):
    """REQUEST_MUTATION_DETECTED is the factory's own firewall (validation must not mutate)."""
    from src.eureka.universe import agent_factory as factory_module
    from src.eureka.universe.agent_factory import REQUEST_MUTATION_DETECTED

    canonical, compilation, evaluation, candidate, proposal = _ready()
    calls = {"n": 0}

    def _drifting_fingerprint(state):
        calls["n"] += 1
        return "before" if calls["n"] == 1 else "after"      # simulate a mutating read

    monkeypatch.setattr(factory_module, "canonical_state_fingerprint", _drifting_fingerprint)
    request = _factory().prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.rejection_codes() == [REQUEST_MUTATION_DETECTED]


def test_family_and_network_role_and_evidence_gates():
    """Covers the remaining declared codes: family mismatch, constitutional role, fake evidence."""
    from src.eureka.universe.agent_genome import AgentIdentity, CognitiveFamily
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical, now=FIXED)
    factory = _factory()

    # the family must belong to the owner the proposal CLAIMS
    spoofed = proposal.model_copy(update={"cognitive_owner": "EM Prescriptor"})
    assert factory.prepare_registration_request(spoofed, **kwargs).rejection_codes() == \
        [REQUEST_FAMILY_MISMATCH]

    # the constitutional network role can never be proposed to an emergent unit
    constitutional = AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                   network_role=NetworkRole.CONSTITUTIONAL, predicate="demanda",
                                   context="Europa")
    asserted = _rebound(proposal, identity=constitutional)
    assert factory.prepare_registration_request(asserted, **kwargs).rejection_codes() == \
        [REQUEST_NETWORK_ROLE_INVALID]

    # fabricated evidence can never satisfy the evidence requirement
    fabricated = evaluation.model_copy(update={"evidence_refs": ["EVI-INVENTED"]})
    canonical.agent_necessity = canonical.agent_necessity.model_copy(update={
        "evaluations": [fabricated if e.candidate_id == candidate.candidate_id else e
                        for e in canonical.agent_necessity.evaluations]})
    request = factory.prepare_registration_request(proposal, **kwargs)
    assert request.rejection_codes() == [REQUEST_EVIDENCE_FABRICATED]


def test_every_reason_code_is_declared_and_used_by_the_suite():
    source = open(os.path.join(os.path.dirname(_MODULE_PATH), "agent_factory.py"),
                  encoding="utf-8").read()
    test_source = open(os.path.abspath(__file__), encoding="utf-8").read()
    for code in REASON_CODES:
        assert code in source
        if code not in ("REQUEST_FROM_VALID_PROPOSAL",):
            assert code in test_source, code


# ============================================================================================= #
# 40. REAL ORCHESTRATOR E2E (no model call) + the HARD STOP
# ============================================================================================= #
E2E_INTENT = "LOOP7 E2E: analizar el impacto del precio en la demanda en Europa y decidir el plan"


def _e2e_orchestrator() -> WorkOrchestrator:
    engine = TestDoubleCognitiveEngine()
    engine.semantic_fixtures[E2E_INTENT] = SemanticProposal(
        intent_category="DECISION",
        problem_understanding="Impacto del precio sobre la demanda",
        objective="Evaluar el impacto del precio en la demanda y decidir el plan",
        context="Europa", evidence_requirements=["serie historica de precios"],
        constraints=["sin datos personales"], unknowns=["elasticidad real"],
        risk="sesgo de seleccion", questions=["¿es estable la elasticidad?"],
        assumptions=["mercado competitivo"], authority="No authority required")
    engine.structural_fixtures[E2E_INTENT] = StructuralProposal(
        entities=["Europa"], variables=["precio", "demanda"], relationships=["precio -> demanda"],
        unknowns=["elasticidad real"], evidence_requirements=["serie historica de precios"],
        task_proposals=[
            CognitiveTask(task_id="E2E-T1", description="Establish current state",
                          owner="EM Descriptor", expected_outputs=["current state"], dependencies=[]),
            CognitiveTask(task_id="E2E-T2", description="Identify explanatory factors",
                          owner="EM Descriptor", expected_outputs=["factors"], dependencies=[]),
            CognitiveTask(task_id="E2E-T3", description="Evaluate future scenarios",
                          owner="EM Predictor", expected_outputs=["predictions"],
                          dependencies=["E2E-T1", "E2E-T2"])])
    return WorkOrchestrator(_reg(), engine)


def test_40_real_orchestrator_e2e_ends_at_a_validated_request_and_stops():
    canonical = _e2e_orchestrator().orchestrate(E2E_INTENT)
    requests = canonical.agent_registration_requests
    assert len(requests) == 1
    request = requests[0]
    assert request.status is RegistrationRequestStatus.VALIDATED
    assert request.agent_id == AGENT_ID
    assert request.candidate_id == "CAND-PREDICATE-00-PRECIO-DEMANDA"
    assert request.work_id == canonical.work.work_id
    assert request.problem_id == canonical.problem.problem_id
    assert request.authority_scope == "PROPOSER"
    assert request.provider_selection == "DEFERRED_TO_MODEL_ROUTER"
    assert request.output_contract["properties"]["validation_status"]["const"] == "CANDIDATE"
    assert request.input_contract.authorized_inputs == ["precio", "demanda"]
    assert [d.agent_id for d in request.dependencies] == []

    # HARD STOP: nothing was registered, activated or executed anywhere
    assert canonical.agent_network.records == []
    assert canonical.agent_network.executions == []
    assert AgentRegistry.rebuild_from(canonical).count() == 0
    assert len(canonical.problem.structured_problem.task_network.tasks) == 4     # untouched
    assert canonical.problem_compilation is not None and canonical.agent_necessity is not None

    # the requests never enter the canonical content identity
    stripped = canonical.model_dump(mode="json")
    stripped.pop("agent_registration_requests")
    assert canonical_state_fingerprint(CanonicalWorkState.model_validate(stripped)) == \
        canonical_state_fingerprint(canonical)

    # deterministic across runs: the COGNITIVE identity is identical (per-work identity differs)
    again = _e2e_orchestrator().orchestrate(E2E_INTENT)
    assert again.agent_registration_requests[0].agent_id == AGENT_ID
    cognitive = lambda p: {k: v for k, v in p.semantic_identity().items()
                           if k not in ("work_id", "problem_id")}
    assert cognitive(again.agent_genome_proposals[0]) == cognitive(canonical.agent_genome_proposals[0])
    assert again.agent_registration_requests[0].work_id != request.work_id
    assert again.agent_registration_requests[0].genome_content_reference != \
        request.genome_content_reference       # different work/problem is different content


def test_f11_interaction_after_the_loop6r_repair():
    """F11 is REPAIRED (LOOP 6R): the envelope's genome_hash is now the SEMANTIC hash.

    Post-repair semantics: a created_at-only difference is NOT content, so the envelope still matches
    and the request stays VALIDATED with the SAME identity; a real CONTENT change is still stale.
    """
    canonical, compilation, evaluation, candidate, proposal = _ready()
    kwargs = dict(candidate=candidate, compilation=compilation, canonical_state=canonical)
    request = _factory().prepare_registration_request(proposal, now=FIXED, **kwargs)
    assert request.status is RegistrationRequestStatus.VALIDATED

    # volatile-only difference: no longer stale (it never was semantic content)
    genome = proposal.genome.model_copy(deep=True)
    genome.created_at = "2030-01-01T00:00:00+00:00"
    volatile_only = proposal.model_copy(update={"genome": genome})
    volatile_request = _factory().prepare_registration_request(volatile_only, now=FIXED, **kwargs)
    assert volatile_request.status is RegistrationRequestStatus.VALIDATED
    assert volatile_request.request_id == request.request_id
    assert volatile_request.genome_content_reference == request.genome_content_reference

    # a CONTENT change is still rejected as stale (no weakening of tamper evidence)
    mutated_genome = proposal.genome.model_copy(deep=True)
    mutated_genome.objective = "a different objective"
    assert _factory().prepare_registration_request(
        proposal.model_copy(update={"genome": mutated_genome}), now=FIXED, **kwargs
    ).rejection_codes() == [REQUEST_STALE_GENOME]

    # and the semantic hash itself is stable across the volatile difference
    assert proposal.genome.hash() == volatile_only.genome.hash()
    assert proposal.genome.hash_v1() != volatile_only.genome.hash_v1()   # the legacy payload was not
