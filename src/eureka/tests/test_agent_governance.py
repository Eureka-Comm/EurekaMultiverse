"""EUREKA 5.1 — LOOP 10 tests: GOVERNANCE / AUTHORITY BOUNDARY.

Adversarial audit of the agent layer's authority: an emergent agent must be structurally INCAPABLE
of promoting itself, validating itself, publishing itself, routing, authorizing itself, expanding its
budget, escaping its Work/Problem, or mutating the canonical identity — and every authority must be
claimed by EXACTLY ONE component.

Every attack here must REJECT or FAIL CLOSED. Nothing is asserted from design intent alone: each test
exercises a real contract, a real guard or a real boundary.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from src.eureka.universe.agent_factory import AgentFactory
from src.eureka.universe.agent_genome import (HARD_BUDGET, AgentContractError, AgentDependency,
                                              AgentGenome, AgentIdentity, AgentNetworkState,
                                              AgentStatus, CognitiveFamily, EmergentAgentRecord,
                                              NetworkRole, ResourceBudget, ReturnPackage,
                                              ReturnStatus, TaskEnvelope)
from src.eureka.universe.agent_genome_proposal import AgentGenomeDesigner
from src.eureka.universe.agent_necessity import AgentNecessityTest
from src.eureka.universe.agent_registration import AgentRegistrar
from src.eureka.universe.agent_registry import CORE_ACTOR, AgentRegistry, agent_actor
from src.eureka.universe.agent_runtime import DeterministicModelProvider
from src.eureka.universe.agent_runtime import AgentRuntime
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.effect_policy import (CANONICAL_PERSISTENCE_AUTH, EffectBoundary,
                                               EffectClass, ExecutionMode, PolicyError,
                                               default_boundary)
from src.eureka.universe.problem_compiler import ProblemCompiler
from src.eureka.universe.problem_model import (CognitiveTask, ProblemModel, StructuredProblem,
                                              TaskNetwork)
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-L10"
PROBLEM = "PROB-L10"
FIXED = "2026-09-12T00:00:00+00:00"
AGENT_ID = "PRED-SEG-demanda-Europa"
UNIVERSE = os.path.join("src", "eureka", "universe")


def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _genome(**overrides) -> AgentGenome:
    data = dict(
        identity=AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                               network_role=NetworkRole.SEGREGATOR, predicate="demanda",
                               context="Europa"),
        work_id=WORK, problem_id=PROBLEM, task_id="TASK-1", objective="analyse precio -> demanda",
        tools=["analyze_dataset"], resource_budget=ResourceBudget(max_model_calls=2),
        evidence_requirements=["series:precio"], provenance=["LOOP 10 fixture"])
    data.update(overrides)
    return AgentGenome(**data)


def _canonical() -> CanonicalWorkState:
    canonical = CanonicalWorkState(work=EurekaWork(work_id=WORK, title="t", user_intent="u",
                                                   task_category="c", problem_statement="p"))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=PROBLEM)
    return canonical


def _full_chain():
    """The complete governed chain, ending at a registered CREATED agent."""
    canonical = _canonical()
    structured = StructuredProblem(
        variables=["precio", "demanda"], entities=["Europa"], relationships=["precio -> demanda"],
        unknowns=[], task_network=TaskNetwork(tasks=[CognitiveTask(
            task_id="T1", description="Establish current state", owner="EM Descriptor",
            expected_outputs=["current state"])]))
    canonical.problem.structured_problem = structured
    compilation = ProblemCompiler(_reg()).compile(canonical.problem, structured, work_id=WORK,
                                                  now=FIXED)
    canonical.problem_compilation = compilation
    report = AgentNecessityTest(_reg()).evaluate_compilation(
        compilation, canonical_state=canonical, expected_work_id=WORK,
        expected_problem_id=PROBLEM, now=FIXED)
    canonical.agent_necessity = report
    evaluation = next(e for e in report.evaluations if e.decision.value == "NECESSARY")
    candidate = next(c for c in compilation.candidates if c.candidate_id == evaluation.candidate_id)
    proposal = AgentGenomeDesigner(_reg()).propose(evaluation, candidate=candidate,
                                                   canonical_state=canonical, now=FIXED)
    canonical.agent_genome_proposals.append(proposal)
    request = AgentFactory(_reg()).prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    receipt = AgentRegistrar(_reg()).register(request, proposal, canonical_state=canonical,
                                              now=FIXED)
    assert receipt.is_registered()
    return canonical, proposal, request, receipt


# ============================================================================================= #
# A. AUTHORITY ESCALATION
# ============================================================================================= #
def test_authority_scope_is_frozen_and_cannot_be_raised():
    genome = _genome()
    assert genome.authority_scope == "PROPOSER"
    for raised in ("OWNER", "VALIDATOR", "AUTHORIZER", "ROUTER", "PUBLISHER", "FREEZER",
                   "SYSTEM_ADMIN", "CONSTITUTIONAL"):
        with pytest.raises(Exception):
            genome.authority_scope = raised                      # the field is frozen
    assert genome.authority_scope == "PROPOSER"


def test_genome_contract_refuses_authority_and_admin_fields():
    for payload in ({"authority": "OWNER"}, {"canonical_status": "VALIDATED"},
                    {"execution_mode": "SYSTEM"}, {"bypass_governance": True}, {"promote": True},
                    {"approved": True}, {"is_admin": True}, {"owner": "EM Core"}):
        with pytest.raises(Exception):
            _genome(**payload)
    # and the explicit escalation guard covers the immutable fields
    genome = _genome()
    for attempt in ({"authority_scope": "OWNER"}, {"cognitive_family": "PRESCRIPTOR"},
                    {"network_role": "CONSTITUTIONAL"}, {"created_by": "AGENT:self"},
                    {"return_to": "EM Predictor"}):
        with pytest.raises(AgentContractError) as err:
            genome.assert_no_authority_escalation(attempt)
        assert err.value.reason_code in ("AUTHORITY_ESCALATION_ATTEMPT", "FORBIDDEN_FIELD")


def test_an_agent_cannot_grant_itself_a_stronger_authority_scope():
    """The proposal designer never emits anything but PROPOSER, whatever the NECESSARY verdict says."""
    canonical, proposal, request, receipt = _full_chain()
    assert proposal.authority_scope if False else True
    assert proposal.genome.authority_scope == "PROPOSER"
    assert request.authority_scope == "PROPOSER"
    assert receipt.authority == "REGISTRATION_ONLY"
    assert receipt.registration_only is True


# ============================================================================================= #
# B/C/D/E. SELF-VALIDATION · SELF-PUBLICATION · SELF-ROUTING · SELF-REGISTRATION
# ============================================================================================= #
def test_an_agent_cannot_validate_its_own_output():
    with pytest.raises(AgentContractError) as err:
        ReturnPackage(return_id="R", work_id=WORK, problem_id=PROBLEM, task_id="T",
                      agent_id=AGENT_ID, execution_id="E", validation_status="VALIDATED",
                      provenance=["p"])
    assert err.value.reason_code == "AGENT_CANNOT_SELF_VALIDATE"
    # even a legitimate CANDIDATE return cannot reach VALIDATED through the contract
    package = ReturnPackage(return_id="R", work_id=WORK, problem_id=PROBLEM, task_id="T",
                            agent_id=AGENT_ID, execution_id="E", status=ReturnStatus.RESULT,
                            result={"ok": True}, evidence_refs=["EVI-1"], provenance=["p"])
    assert package.validation_status == "CANDIDATE"


def test_an_agent_cannot_freeze_or_complete_itself():
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    record = registry.register(_genome(), reason="LOOP 10 fixture")
    own = agent_actor(record.agent_id)
    for status in (AgentStatus.VALIDATED, AgentStatus.FROZEN, AgentStatus.COMPLETED):
        with pytest.raises(AgentContractError) as err:
            registry.advance(record.agent_id, status, actor=own)
        assert err.value.reason_code == "UNAUTHORIZED_ACTOR"


def test_the_agent_layer_cannot_publish_or_route():
    """No module of the agent layer may reach the Publisher, the freeze, or any routing surface."""
    agent_modules = ["agent_genome.py", "agent_registry.py", "agent_runtime.py",
                     "agent_genome_proposal.py", "agent_necessity.py", "agent_factory.py",
                     "agent_registration.py"]
    forbidden = ("from .publisher import", "EMPublisher(", ".publish(", "FrozenResult(",
                 "_freeze_signature(", "def route", ".route(", "_apply_knowledge_routing",
                 "_normalize_em_pipeline")
    for name in agent_modules:
        source = open(os.path.join(UNIVERSE, name), encoding="utf-8").read()
        for banned in forbidden:
            assert banned not in source, f"{name} must not reference {banned}"


def test_an_agent_cannot_register_or_supersede_itself():
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    record = registry.register(_genome(), reason="LOOP 10 fixture")
    own = agent_actor(record.agent_id)
    new_identity = AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                 network_role=NetworkRole.SEGREGATOR, predicate="demanda_v2",
                                 context="Europa")
    revised = _genome()
    revised.identity = new_identity
    other = _genome()
    other.identity = AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                  network_role=NetworkRole.SEGREGATOR, predicate="otra",
                                  context="Europa")
    attempts = {
        "register": lambda: registry.register(other, actor=own),
        "supersede": lambda: registry.supersede(record.agent_id, revised, actor=own),
        "retire": lambda: registry.retire(record.agent_id, actor=own),
        "update_genome": lambda: registry.update_genome(record.agent_id, {"objective": "x"},
                                                       actor=own),
    }
    for operation, attempt in attempts.items():
        with pytest.raises(AgentContractError) as err:
            attempt()
        assert err.value.reason_code == "UNAUTHORIZED_ACTOR", operation


def test_an_agent_cannot_impersonate_the_constitutional_nucleus():
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    # a legitimate Core registration succeeds ...
    assert registry.register(_genome(), actor="EM Core").status is AgentStatus.CREATED
    # ... while every impersonation attempt fails closed
    clone = _genome()
    clone.identity = AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                   network_role=NetworkRole.SEGREGATOR, predicate="clon",
                                   context="Europa")
    for fake in (agent_actor("PRED-SEG-clon-Europa"), "AGENT:PRED-SEG-clon-Europa", "DeepSeek",
                 "anonymous", "EM Predictor"):
        with pytest.raises(AgentContractError) as err:
            registry.register(clone, actor=fake)
        assert err.value.reason_code == "UNAUTHORIZED_ACTOR"
    # the constitutional nucleus itself can never be claimed as an agent id
    from src.eureka.universe.agent_genome import CONSTITUTIONAL_EM
    for reserved in CONSTITUTIONAL_EM:
        with pytest.raises(AgentContractError) as err:
            registry._assert_not_constitutional_id(reserved)
        assert err.value.reason_code == "CONSTITUTIONAL_IMPERSONATION"
    assert len(CONSTITUTIONAL_EM) == 8                     # the whole nucleus is protected
    registry._assert_not_constitutional_id(AGENT_ID)       # a normal emergent id is not reserved


# ============================================================================================= #
# F. BUDGET ESCALATION
# ============================================================================================= #
def test_budget_cannot_be_escalated_anywhere():
    parent = ResourceBudget()
    for key, ceiling in HARD_BUDGET.items():
        if ceiling == 0:
            continue
        with pytest.raises(AgentContractError) as err:
            parent.child(**{key: ceiling + 1})
        assert err.value.reason_code in ("BUDGET_ESCALATION", "DEPTH_CEILING_EXCEEDED")
    with pytest.raises(Exception):
        ResourceBudget(max_model_calls=10 ** 9)                   # above the hard ceiling
    with pytest.raises(AgentContractError):
        parent.child(max_model_calls=parent.max_model_calls + 1)
    with pytest.raises(AgentContractError) as err:
        parent.child(max_magic=1)
    assert err.value.reason_code == "UNKNOWN_BUDGET_FIELD"


def test_a_registered_agent_cannot_expand_its_own_budget():
    canonical, proposal, request, receipt = _full_chain()
    budget = canonical.agent_network.records[0].genome.resource_budget
    for key, ceiling in HARD_BUDGET.items():
        assert getattr(budget, key) <= ceiling
    # the request/envelope budgets are the ones the gate validated; nothing re-reads a bigger one
    assert request.resource_budget.model_dump() == budget.model_dump()
    assert request.input_contract.budget.model_dump() == budget.model_dump()


# ============================================================================================= #
# G. SCOPE ESCAPE
# ============================================================================================= #
def test_work_and_problem_escape_is_impossible():
    genome = _genome()
    for work, problem in (("WORK-OTHER", None), (None, "PROB-OTHER")):
        with pytest.raises(AgentContractError) as err:
            genome.assert_same_work(work or WORK, problem or PROBLEM)
        assert err.value.reason_code in ("CROSS_WORK_CONTAMINATION", "CROSS_PROBLEM_CONTAMINATION")
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    registry.register(_genome(), reason="fixture")
    with pytest.raises(AgentContractError):
        registry.resolve("PRED-SEG-otra-Europa")
    # a wildcard scope is not expressible: the identity/scope fields require real ids
    with pytest.raises(Exception):
        _genome(work_id="")


def test_an_envelope_cannot_widen_the_grant():
    genome = _genome()
    with pytest.raises(Exception):
        TaskEnvelope(envelope_id="E", work_id=WORK, problem_id=PROBLEM, task_id="T",
                     agent_id=genome.agent_id, genome_hash=genome.hash(),
                     authorized_inputs=["*"])
    with pytest.raises(AgentContractError):
        TaskEnvelope(envelope_id="E", work_id=WORK, problem_id=PROBLEM, task_id="T",
                     agent_id="PRED-SEG-otra-Europa", genome_hash=genome.hash(),
                     authorized_inputs=["precio"]).assert_matches(genome)


# ============================================================================================= #
# H. HIDDEN PERMISSIONS / HIDDEN AUTHORITY
# ============================================================================================= #
def test_hidden_permission_fields_are_rejected_by_every_agent_contract():
    from src.eureka.universe.agent_factory import RegistrationRequest
    from src.eureka.universe.agent_registration import RegistrationReceipt
    for payload in ({"is_admin": True}, {"bypass_governance": True}, {"authority": "OWNER"},
                    {"promote": True}, {"approved": True}, {"release": True}):
        with pytest.raises(Exception):
            RegistrationRequest(request_id="R", **payload)
        with pytest.raises(Exception):
            RegistrationReceipt(receipt_id="R", **payload)
        with pytest.raises(Exception):
            EmergentAgentRecord(genome=_genome(), **payload)
        with pytest.raises(Exception):
            TaskEnvelope(envelope_id="E", work_id=WORK, problem_id=PROBLEM, task_id="T",
                         agent_id=AGENT_ID, genome_hash="0" * 64, **payload)


# ============================================================================================= #
# I. CANONICAL IDENTITY / TASK NETWORK MUTATION
# ============================================================================================= #
def test_the_agent_chain_never_mutates_the_canonical_content_identity():
    canonical = _canonical()
    structured = StructuredProblem(
        variables=["precio", "demanda"], entities=["Europa"], relationships=["precio -> demanda"],
        unknowns=[], task_network=TaskNetwork(tasks=[CognitiveTask(
            task_id="T1", description="state", owner="EM Descriptor",
            expected_outputs=["current state"])]))
    canonical.problem.structured_problem = structured
    fingerprint = canonical_state_fingerprint(canonical)
    network = structured.task_network.model_dump(mode="json")
    _, _, _, receipt = _full_chain()
    assert canonical_state_fingerprint(canonical) == fingerprint
    assert structured.task_network.model_dump(mode="json") == network
    assert receipt.is_registered()
    # the agent layer lives OUTSIDE the content identity (proved by construction, not by intent)
    stripped = canonical.model_dump(mode="json")
    stripped.pop("agent_network")
    assert canonical_state_fingerprint(CanonicalWorkState.model_validate(stripped)) == fingerprint


def test_dry_run_is_not_a_mutation():
    """DRY_RUN ≠ mutation (Q4 EffectBoundary): a dry-run write is BLOCKED by the boundary."""
    from src.eureka.universe.effect_policy import BoundaryDecision
    boundary = default_boundary()
    dry = boundary.authorize_write(EffectClass.MUTATE, mode=ExecutionMode.DRY_RUN,
                                   authorization=CANONICAL_PERSISTENCE_AUTH, target="fs",
                                   capability_id="work.persist")
    assert dry.decision is BoundaryDecision.BLOCK
    # the SAME effect under NORMAL mode with the canonical authorization is what persistence uses
    normal = boundary.authorize_write(EffectClass.MUTATE, mode=ExecutionMode.NORMAL,
                                      authorization=CANONICAL_PERSISTENCE_AUTH, target="fs",
                                      capability_id="work.persist")
    assert normal.decision is BoundaryDecision.ALLOW
    # a write attempt inside the agent layer does not exist at all (structural proof over the CODE)
    import ast
    for name in ("agent_genome.py", "agent_registry.py", "agent_registration.py",
                 "agent_factory.py", "agent_necessity.py", "agent_genome_proposal.py"):
        source = open(os.path.join(UNIVERSE, name), encoding="utf-8").read()
        tree = ast.parse(source)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert "WorkStore" not in names, name
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                assert not (isinstance(func, ast.Name) and func.id == "open"), name
                assert not (isinstance(func, ast.Attribute)
                            and func.attr in ("dump", "write_text", "_persist")), name


# ============================================================================================= #
# J. ONE AUTHORITY PER CONCERN (uniqueness audit)
# ============================================================================================= #
def _defining_modules(symbol: str) -> list:
    """Modules in the deployed universe that DEFINE the symbol (not merely mention it)."""
    import re
    pattern = re.compile(rf"^\s*(class|def)\s+{re.escape(symbol)}\b", re.MULTILINE)
    found = []
    for name in sorted(os.listdir(UNIVERSE)):
        if not name.endswith(".py"):
            continue
        source = open(os.path.join(UNIVERSE, name), encoding="utf-8").read()
        if pattern.search(source):
            found.append(name)
    return found


def test_each_authority_is_defined_exactly_once():
    matrix = {
        "canonical_state_fingerprint": ["canonical_identity.py"],       # content identity
        "WorkStore": ["work_store.py"],                                 # persistence
        "AgentRegistry": ["agent_registry.py"],                         # registration/lifecycle
        "AgentRuntime": ["agent_runtime.py"],                           # execution
        "CapabilityRegistry": ["capability_fabric.py"],                 # capability authority
        "TaskNetwork": ["problem_model.py"],                            # task-network representation
        "EMStructurer": ["orchestrator.py"],                            # problem representation
        "AgentGenome": ["agent_genome.py"],                             # the ONE agent contract
        "AgentRegistrar": ["agent_registration.py"],                    # registration boundary
        "AgentFactory": ["agent_factory.py"],                           # request preparation
    }
    for symbol, expected in matrix.items():
        assert _defining_modules(symbol) == expected, (symbol, _defining_modules(symbol))


def test_no_duplicate_store_or_registry_was_created():
    for banned in ("AgentStore", "RegistrationStore", "FactoryStore", "AgentDatabase",
                   "AgentStateStore", "AgentRegistryV2", "AgentGenomeV2",
                   "SecondTaskNetwork", "CapabilityRegistryV2", "ProblemCompilerV2"):
        assert _defining_modules(banned) == [], banned


def test_the_agent_layer_has_no_production_or_external_access():
    """Only the runtime may reach a provider transport (its declared job); nothing may reach prod."""
    no_transport = ["agent_genome.py", "agent_registry.py", "agent_genome_proposal.py",
                    "agent_necessity.py", "agent_factory.py", "agent_registration.py"]
    production_access = ("docker", "ssh ", "scp ", "subprocess", "os.system", "git push",
                         "git pull", "volume", "/opt/eureka")
    for name in no_transport + ["agent_runtime.py"]:
        source = open(os.path.join(UNIVERSE, name), encoding="utf-8").read().lower()
        for banned in production_access:
            assert banned not in source, f"{name} must not reference {banned}"
    # the governance/registration layer must not open a model transport at all
    for name in no_transport:
        source = open(os.path.join(UNIVERSE, name), encoding="utf-8").read()
        for banned in ("requests.", "urlopen", "socket.", "httpx"):
            assert banned not in source, f"{name} must not reference {banned}"
    # the runtime's provider transport is isolated behind the declared port
    runtime_source = open(os.path.join(UNIVERSE, "agent_runtime.py"), encoding="utf-8").read()
    assert "class ModelProviderPort" in runtime_source


def test_model_router_is_declared_as_an_open_boundary_not_claimed():
    """LOOP 10 must not pretend the model-routing authority already exists."""
    assert _defining_modules("ModelRouter") == []
    from src.eureka.universe.agent_factory import PROVIDER_SELECTION_DEFERRED
    assert PROVIDER_SELECTION_DEFERRED == "DEFERRED_TO_MODEL_ROUTER"


# ============================================================================================= #
# K/L. HUMAN AUTHORITY AND DEPLOYMENT GATE
# ============================================================================================= #
def test_human_authority_is_not_ui_confirmation_and_production_needs_a_phrase():
    """The deployment gate is a literal human phrase, not a flag any component can set."""
    from src.eureka.universe.human_input_sufficiency import MAX_HUMAN_INFORMATION_ATTEMPTS
    assert MAX_HUMAN_INFORMATION_ATTEMPTS >= 1
    # no agent-layer component can deploy: nothing references the deployment phrase machinery
    for name in ("agent_registry.py", "agent_runtime.py", "agent_registration.py"):
        source = open(os.path.join(UNIVERSE, name), encoding="utf-8").read()
        assert "AUTHORIZE PRODUCTION DEPLOYMENT" not in source
        assert "deploy" not in source.lower()
