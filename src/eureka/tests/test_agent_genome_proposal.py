"""EUREKA 5.1 — LOOP 6 tests: EMERGENT AGENT GENOME PROPOSAL (proposal only; nothing is registered).

Mandated coverage (Harness LOOP 6, 35 cases):
  1 NECESSARY -> valid proposal · 2 NOT_NECESSARY cannot generate · 3 BLOCKED cannot generate ·
  4 authority remains PROPOSER · 5 output remains CANDIDATE · 6 identity deterministic ·
  7 identity collision rejected · 8 family ownership valid · 9 no role creep ·
  10 no provider selected by the genome · 11 budget bounded · 12 evidence requirement preserved ·
  13 evidence not fabricated · 14 input contract narrow · 15 output contract narrow ·
  16 dependencies valid · 17 dependency cycle rejected · 18 cross-work rejected ·
  19 cross-problem rejected · 20 frozen genome immutable · 21 serialization deterministic ·
  22 same candidate -> same genome semantics · 23 different candidate -> different identity ·
  24 no registry mutation · 25 no AgentRuntime invocation · 26 no model call ·
  27 no TaskNetwork mutation · 28 canonical problem unchanged · 29 live data unchanged ·
  30 WorkStore round-trip · 31 restart/reload identical · 32 adversarial authority escalation ·
  33 adversarial provider substitution · 34 adversarial budget escalation ·
  35 adversarial policy mutation.
"""
import ast
import inspect
import json
import os
import tempfile

import pytest

from src.eureka.universe.agent_genome import (CONSTITUTIONAL_EM, FAMILY_OWNER, HARD_BUDGET,
                                             AgentContractError, AgentDependency,
                                             AgentDependencyKind, AgentGenome, AgentIdentity,
                                             AgentNetworkState, AgentStatus, CognitiveFamily,
                                             EmergentAgentRecord, NetworkRole, ResourceBudget)
from src.eureka.universe.agent_genome_proposal import (FORBIDDEN_OPERATIONS,
                                                       GENOME_AUTHORITY,
                                                       GENOME_AUTHORITY_ESCALATION,
                                                       GENOME_BUDGET_ESCALATION,
                                                       GENOME_CROSS_PROBLEM, GENOME_CROSS_WORK,
                                                       GENOME_DEPENDENCY_CYCLE,
                                                       GENOME_DEPENDENCY_UNRESOLVABLE,
                                                       GENOME_DUPLICATES_EXISTING,
                                                       GENOME_EVIDENCE_FABRICATED,
                                                       GENOME_IDENTITY_COLLISION,
                                                       GENOME_INPUT_CONTRACT_TOO_BROAD,
                                                       GENOME_NETWORK_ROLE_REFUSED,
                                                       GENOME_OUTPUT_CONTRACT_NOT_CANDIDATE,
                                                       GENOME_POLICY_MUTATION, GENOME_PROVIDER_PIN,
                                                       GENOME_REGISTRY_REQUESTED,
                                                       GENOME_RUNTIME_REQUESTED,
                                                       GENOME_TASKNETWORK_MUTATION_REQUESTED,
                                                       GENOME_VERDICT_NOT_NECESSARY,
                                                       OUTPUT_STATUS_CANDIDATE,
                                                       PROVIDER_SELECTION_DEFERRED,
                                                       PROPOSAL_AUTHORITY, REASON_CODES,
                                                       AgentGenomeDesigner, AgentGenomeProposal,
                                                       GenomeDesignRequest, GenomeProposalError,
                                                       GenomeProposalStatus)
from src.eureka.universe.agent_necessity import (AgentNecessityTest, NecessityDecision,
                                                 NecessityEvaluation)
from src.eureka.universe.agent_registry import AgentRegistry
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.canonical_state import CanonicalWorkState, ExecutionPlan
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.cognitive_engine import (SemanticProposal, StructuralProposal,
                                                 TestDoubleCognitiveEngine)
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.problem_compiler import (CandidateKind, ProblemCandidate,
                                                 ProblemCompilation, ProblemCompiler)
from src.eureka.universe.problem_model import (CognitiveTask, ProblemModel, StructuredProblem,
                                              TaskNetwork)
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-L6"
PROBLEM = "PROB-L6"
FIXED = "2026-09-12T00:00:00+00:00"
NEW_AGENT_ID = "PRED-SEG-demanda-Europa"
_UNIVERSE_DIR = os.path.dirname(os.path.abspath(inspect.getfile(AgentGenomeDesigner)))
_MODULE_PATH = os.path.join(_UNIVERSE_DIR, "agent_genome_proposal.py")
_FORENSIC_PRE = os.path.join("_scratch", "loop6", "FORENSIC_PRE.json")


# -------------------------------------------------------------------------------------------- #
# helpers
# -------------------------------------------------------------------------------------------- #
def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _designer() -> AgentGenomeDesigner:
    return AgentGenomeDesigner(_reg())


def _task(task_id="T1", owner="EM Descriptor", description="Establish current state",
          outputs=("current state",)) -> CognitiveTask:
    return CognitiveTask(task_id=task_id, description=description, owner=owner,
                         expected_outputs=list(outputs), dependencies=[])


def _canonical(*, work_id=WORK, problem_id=PROBLEM, variables=("precio", "demanda"),
               relationships=("precio -> demanda",), context="Europa", tasks=None,
               evidence_ids=(), agents=None) -> CanonicalWorkState:
    canonical = CanonicalWorkState(
        work=EurekaWork(work_id=work_id, title="t", user_intent="u", task_category="c",
                        problem_statement="p"))
    structured = StructuredProblem(variables=list(variables), entities=["Europa"],
                                   relationships=list(relationships), unknowns=[])
    structured.task_network = TaskNetwork(tasks=list(tasks if tasks is not None else [_task()]))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=problem_id,
                                     context=context, structured_problem=structured)
    canonical.execution_plan = ExecutionPlan()
    canonical.evidence_ids = list(evidence_ids)
    if agents:
        canonical.agent_network = AgentNetworkState(records=list(agents))
    return canonical


def _agent_record(predicate="otro", family=CognitiveFamily.PREDICTOR,
                  role=NetworkRole.SEGREGATOR, context="Europa", dependencies=(),
                  work_id=WORK, problem_id=PROBLEM) -> EmergentAgentRecord:
    genome = AgentGenome(
        identity=AgentIdentity(cognitive_family=family, network_role=role, predicate=predicate,
                               context=context),
        work_id=work_id, problem_id=problem_id, task_id=f"TASK-{predicate}",
        objective=f"existing unit for {predicate}", tools=[], evidence_requirements=[],
        resource_budget=ResourceBudget(max_model_calls=1),
        dependencies=[AgentDependency(agent_id=d, kind=AgentDependencyKind.DATA) for d in dependencies],
        provenance=["LOOP 6 test fixture"])
    return EmergentAgentRecord(genome=genome, status=AgentStatus.CREATED)


def _pipeline(canonical: CanonicalWorkState):
    """Run the REAL LOOP 4 + LOOP 5 stages over the canonical state's problem."""
    compilation = ProblemCompiler(_reg()).compile(
        canonical.problem, canonical.problem.structured_problem,
        work_id=canonical.work.work_id, now=FIXED)
    report = AgentNecessityTest(_reg()).evaluate_compilation(
        compilation, canonical_state=canonical, expected_work_id=canonical.work.work_id,
        expected_problem_id=canonical.problem.problem_id, now=FIXED)
    return compilation, report


def _necessary(canonical=None):
    canonical = canonical or _canonical()
    compilation, report = _pipeline(canonical)
    evaluation = next(e for e in report.evaluations if e.decision is NecessityDecision.NECESSARY)
    candidate = next(c for c in compilation.candidates if c.candidate_id == evaluation.candidate_id)
    return canonical, compilation, report, evaluation, candidate


def _propose(canonical=None, **kw) -> AgentGenomeProposal:
    canonical, _, _, evaluation, candidate = _necessary(canonical)
    return _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                               now=FIXED, **kw)


def _synthetic_necessary(**overrides) -> NecessityEvaluation:
    data = dict(evaluation_id="EVAL-SYNTH", candidate_id="CAND-SYNTH",
                candidate_kind=CandidateKind.PREDICATE, work_id=WORK, problem_id=PROBLEM,
                decision=NecessityDecision.NECESSARY,
                reason_code="NECESSARY_EMERGENT_UNIT_JUSTIFIED", owner="EM Predictor",
                responsibility_boundary="DIFFERENTIATED", duplication_check="NO_DUPLICATION",
                authority_check="PROPOSER_ONLY", routing_check="NO_ROUTING",
                validation_check="EXTERNAL_VALIDATION_AVAILABLE", resource_check="FEASIBLE",
                input_contract="precio", output_contract="demanda",
                capability_gap_evidence="only generic capabilities exist")
    data.update(overrides)
    return NecessityEvaluation(**data)


# ============================================================================================= #
# 0. SURFACE / AUTHORITY / NON-DUPLICATION
# ============================================================================================= #
def test_public_surface_has_no_registry_runtime_or_provider_api():
    public = [m for m in dir(AgentGenomeDesigner) if not m.startswith("_")]
    methods = [m for m in public if callable(getattr(AgentGenomeDesigner, m))]
    assert public == ["AUTHORITY", "GENOME_AUTHORITY", "propose"]
    assert methods == ["propose"]
    for marker in ("register", "activate", "execute", "run", "route", "persist", "store", "publish",
                   "freeze", "validate", "provider", "model", "create"):
        assert not any(marker in m.lower() for m in methods), marker


def test_module_never_imports_the_registry_runtime_store_or_a_provider():
    tree = ast.parse(open(_MODULE_PATH, encoding="utf-8").read())
    forbidden = ("agent_registry", "agent_runtime", "agent_definition", "work_store",
                 "canonical_state", "eureka.foundation", "eureka_cognitive_sdk", "requests",
                 "httpx", "socket", "urllib", "openai", "deepseek", "ollama", "os")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(forbidden), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(forbidden), node.module
    # CODE-level names (prose in the docstring is not a dependency)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for banned_name in ("AgentRuntime", "AgentRegistry", "WorkStore", "CanonicalWorkState",
                        "AgentDefinition", "ModelProviderPort", "DeepSeekModelProvider"):
        assert banned_name not in used, banned_name
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            assert not (isinstance(node.func, ast.Name) and node.func.id == "open")
            assert not (isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("execute", "run", "register", "persist", "dump"))


def test_the_genome_contract_is_embedded_not_redefined():
    """No parallel agent schema: the proposal carries the EXISTING AgentGenome type."""
    annotations = {name: str(field.annotation)
                   for name, field in AgentGenomeProposal.model_fields.items()}
    assert "AgentGenome" in annotations["genome"]
    assert "TaskEnvelope" in annotations["input_contract"]
    # the wrapper does not clone genome fields
    for cloned in ("identity", "objective", "predicates", "model_requirements", "resource_budget",
                   "forbidden_operations", "authority_scope", "tools", "evidence_requirements"):
        assert cloned not in AgentGenomeProposal.model_fields, cloned
    assert not any(name.endswith("Genome") and name not in ("genome",)
                   for name in AgentGenomeProposal.model_fields)


def test_designer_is_stateless():
    designer = _designer()
    _propose()
    assert list(designer.__dict__.keys()) == ["cap_registry"]


def test_reason_codes_are_declared_and_unique():
    assert len(set(REASON_CODES)) == len(REASON_CODES)
    assert len(REASON_CODES) == 25
    assert GENOME_DUPLICATES_EXISTING in REASON_CODES and GENOME_PROVIDER_PIN in REASON_CODES


# ============================================================================================= #
# 1-23. THE MANDATED DESIGN CASES
# ============================================================================================= #
def test_1_necessary_candidate_produces_a_valid_genome_proposal():
    canonical, compilation, report, evaluation, candidate = _necessary()
    proposal = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                   now=FIXED)
    assert proposal.status is GenomeProposalStatus.PROPOSED
    assert proposal.is_valid_proposal() is True
    assert proposal.genome is not None
    assert proposal.candidate_id == evaluation.candidate_id
    assert proposal.necessity_decision == "NECESSARY"
    assert proposal.necessity_reason_code == "NECESSARY_EMERGENT_UNIT_JUSTIFIED"
    assert proposal.source_reference == candidate.source
    assert proposal.boundary == "precio -> demanda"
    assert proposal.cognitive_owner == "EM Predictor"
    assert proposal.proposal_id.startswith("PROP-")
    assert proposal.input_contract is not None and proposal.output_contract
    assert proposal.genome.predicates == ["precio -> demanda"]


def test_2_non_necessary_candidate_cannot_generate_a_genome():
    canonical = _canonical()
    compilation, report = _pipeline(canonical)
    task_eval = next(e for e in report.evaluations
                     if e.decision is NecessityDecision.NOT_NECESSARY)
    task = next(c for c in compilation.candidates if c.candidate_id == task_eval.candidate_id)
    proposal = _designer().propose(task_eval, candidate=task, canonical_state=canonical, now=FIXED)
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.genome is None and proposal.input_contract is None
    assert proposal.rejections[0].reason_code == GENOME_VERDICT_NOT_NECESSARY
    assert proposal.is_valid_proposal() is False


def test_3_blocked_candidate_cannot_generate_a_genome():
    canonical = _canonical(relationships=())
    blocked = _synthetic_necessary(decision=NecessityDecision.BLOCKED,
                                   reason_code="NECESSITY_BOUNDARY_UNCLEAR", owner="EM Predictor",
                                   input_contract="", output_contract="")
    proposal = _designer().propose(blocked, canonical_state=canonical, now=FIXED)
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.genome is None
    assert proposal.rejections[0].reason_code == GENOME_VERDICT_NOT_NECESSARY


def test_4_authority_scope_remains_proposer():
    proposal = _propose()
    assert proposal.genome.authority_scope == "PROPOSER"
    assert proposal.genome.authority_scope == GENOME_AUTHORITY
    with pytest.raises(Exception):
        proposal.genome.authority_scope = "OWNER"            # frozen=True in the contract
    with pytest.raises(GenomeProposalError) as err:
        AgentGenomeProposal(proposal_id="P", authority="AUTHORITY")
    assert err.value.reason_code == "PROPOSAL_AUTHORITY_CANNOT_BE_ESCALATED"
    with pytest.raises(GenomeProposalError):
        AgentGenomeProposal(proposal_id="P", registers_agents=True)
    with pytest.raises(GenomeProposalError):
        AgentGenomeProposal(proposal_id="P", selects_provider=True)
    with pytest.raises(GenomeProposalError):
        AgentGenomeProposal(proposal_id="P", mutates_task_network=True)
    with pytest.raises(GenomeProposalError):
        AgentGenomeProposal(proposal_id="P", provider_selection="CHOSE_DEEPSEEK")


def test_5_output_contract_remains_candidate():
    proposal = _propose()
    schema = proposal.output_contract
    assert schema["properties"]["validation_status"]["const"] == OUTPUT_STATUS_CANDIDATE
    assert schema["additionalProperties"] is False
    # a proposal whose output contract drops the CANDIDATE pin cannot even be constructed
    with pytest.raises(GenomeProposalError) as err:
        AgentGenomeProposal(proposal_id="P", genome=proposal.genome,
                            input_contract=proposal.input_contract,
                            output_contract={"type": "object", "properties": {}})
    assert err.value.reason_code == GENOME_OUTPUT_CONTRACT_NOT_CANDIDATE
    # and the runtime return contract can never be VALIDATED (LOOP 1 contract)
    from src.eureka.universe.agent_genome import ReturnPackage
    with pytest.raises(AgentContractError):
        ReturnPackage(return_id="R", work_id=WORK, problem_id=PROBLEM, task_id="T", agent_id="A",
                      execution_id="E", validation_status="VALIDATED", provenance=["p"])


def test_6_identity_is_deterministic():
    canonical, _, _, evaluation, candidate = _necessary()
    first = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED)
    second = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                 now=FIXED)
    assert first.agent_id() == second.agent_id() == NEW_AGENT_ID
    assert first.semantic_identity() == second.semantic_identity()
    assert first.proposal_id == second.proposal_id
    assert AgentIdentity.parse(first.agent_id()).agent_id == first.agent_id()


def test_7_identity_collision_is_rejected():
    existing = _agent_record(predicate="demanda", context="Europa")
    canonical = _canonical(agents=[existing])
    assert existing.genome.agent_id == NEW_AGENT_ID
    # (the real pipeline would already answer DUPLICATES_AGENT here, so the design-time guard is
    #  exercised with a NECESSARY verdict that claims the same identity)
    proposal = _designer().propose(_synthetic_necessary(), canonical_state=canonical,
                                   candidate=ProblemCandidate(
                                       candidate_id="CAND-SYNTH", kind=CandidateKind.PREDICATE,
                                       source="structured_problem.relationships[0]",
                                       reason="declared relationship",
                                       reference="precio -> demanda",
                                       cognitive_owner="EM Predictor"),
                                   now=FIXED)
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.rejections[0].reason_code == GENOME_IDENTITY_COLLISION
    assert proposal.genome is None


def test_8_family_ownership_is_valid():
    proposal = _propose()
    identity = proposal.genome.identity
    assert identity.cognitive_family is CognitiveFamily.PREDICTOR
    assert identity.cognitive_owner == "EM Predictor"
    assert FAMILY_OWNER[identity.cognitive_family] == identity.cognitive_owner
    assert proposal.genome.return_to == "EM Predictor"
    assert proposal.cognitive_owner == "EM Predictor"
    # one family -> one constitutional owner (no ambiguity in the mapping)
    assert len(set(FAMILY_OWNER.values())) == len(FAMILY_OWNER)
    assert set(FAMILY_OWNER.values()) <= set(CONSTITUTIONAL_EM)
    # an owner without a family is refused
    no_family = _synthetic_necessary(owner="EM Core")
    rejected = _designer().propose(no_family, canonical_state=_canonical(), now=FIXED)
    assert rejected.status is GenomeProposalStatus.REJECTED


def test_9_no_role_creep():
    proposal = _propose()
    assert proposal.genome.identity.network_role is NetworkRole.SEGREGATOR     # narrowest default
    for operation in ("validate_own_output", "freeze_any_artifact", "publish_any_artifact",
                      "route_next_owner", "modify_task_network", "register_any_agent",
                      "create_child_agent", "select_model_provider", "change_policy"):
        assert operation in proposal.genome.forbidden_operations
    assert len(proposal.genome.forbidden_operations) == len(FORBIDDEN_OPERATIONS)
    # the family is NOT requestable at all
    assert "cognitive_family" not in GenomeDesignRequest.model_fields
    assert "authority_scope" not in GenomeDesignRequest.model_fields
    # an emergent unit can never claim the constitutional nucleus
    rejected = _propose(request=GenomeDesignRequest(
        requested_network_role=NetworkRole.CONSTITUTIONAL))
    assert rejected.status is GenomeProposalStatus.REJECTED
    assert rejected.rejections[0].reason_code == GENOME_NETWORK_ROLE_REFUSED
    # the constitutional nucleus itself is never proposed by this designer
    assert proposal.genome.identity.network_role is not NetworkRole.CONSTITUTIONAL


def test_10_model_provider_is_not_selected_by_the_genome():
    proposal = _propose()
    fields = set(AgentGenome.model_fields)
    for provider_key in ("provider", "model", "vendor", "api_key", "endpoint", "base_url", "url"):
        assert provider_key not in fields
    assert proposal.provider_selection == PROVIDER_SELECTION_DEFERRED
    assert proposal.selects_provider is False
    requirement = proposal.genome.model_requirements
    assert requirement.capability_class.value in ("REMOTE_API", "LOCAL_RUNTIME")   # a class, not a vendor
    assert requirement.allow_fallback is False
    from src.eureka.universe.agent_genome import ModelRequirement
    with pytest.raises(Exception):
        ModelRequirement(model="deepseek-chat")          # a vendor pin is not expressible
    with pytest.raises(GenomeProposalError) as err:
        _designer().propose(_synthetic_necessary(), canonical_state=_canonical(),
                            request={"provider": "deepseek"})
    assert err.value.reason_code == GENOME_PROVIDER_PIN


def test_11_resource_budget_is_bounded():
    parent = ResourceBudget()
    proposal = _propose(parent_budget=parent)
    budget = proposal.genome.resource_budget
    for key, ceiling in HARD_BUDGET.items():
        assert getattr(budget, key) <= ceiling, key
        assert getattr(budget, key) <= getattr(parent, key), key
    assert budget.max_model_calls == 2 and budget.max_cost_units == 5      # narrower than parent
    assert proposal.input_contract.budget.model_dump() == budget.model_dump()
    assert "unlimited" not in json.dumps(budget.model_dump()).lower()
    assert "*" not in json.dumps(budget.model_dump())


def test_12_evidence_requirement_is_preserved():
    canonical = _canonical(evidence_ids=("EVI-REAL-1",))
    _, _, _, evaluation, candidate = _necessary(canonical)
    with_evidence = evaluation.model_copy(update={"evidence_refs": ["EVI-REAL-1"]})
    proposal = _designer().propose(with_evidence, candidate=candidate, canonical_state=canonical,
                                   now=FIXED)
    assert proposal.status is GenomeProposalStatus.PROPOSED
    assert proposal.evidence_refs == ["EVI-REAL-1"]
    assert proposal.input_contract.authorized_evidence_ids == ["EVI-REAL-1"]
    assert proposal.genome.requires_evidence() is True
    assert proposal.genome.evidence_requirements == ["series:precio", "series:demanda"]


def test_13_evidence_is_not_fabricated():
    canonical = _canonical(evidence_ids=())
    _, _, _, evaluation, candidate = _necessary(canonical)
    fake = evaluation.model_copy(update={"evidence_refs": ["EVI-INVENTED"]})
    proposal = _designer().propose(fake, candidate=candidate, canonical_state=canonical, now=FIXED)
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.rejections[0].reason_code == GENOME_EVIDENCE_FABRICATED

    # the provenance SOURCE REFERENCE is never converted into evidence
    good = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED)
    assert good.source_reference == "structured_problem.relationships[0]"
    assert good.source_reference not in good.input_contract.authorized_evidence_ids
    assert good.source_reference not in good.evidence_refs
    assert good.source_reference in good.genome.knowledge_sources       # provenance, not evidence


def test_14_input_contract_is_narrow():
    proposal = _propose()
    envelope = proposal.input_contract
    assert envelope.authorized_inputs == ["precio", "demanda"]          # condition + target only
    assert "*" not in envelope.authorized_inputs
    assert not any(broad in json.dumps(envelope.model_dump()).lower()
                   for broad in ("canonical_state", "whole_state", "everything"))
    assert set(envelope.context) == {"boundary", "condition_inputs", "target", "cognitive_family"}
    # an input the work does not declare cannot be granted
    rejected = _propose(request=GenomeDesignRequest(requested_inputs=["secreto_interno"]))
    assert rejected.status is GenomeProposalStatus.REJECTED
    assert rejected.rejections[0].reason_code == GENOME_INPUT_CONTRACT_TOO_BROAD
    # a wildcard is refused by the canonical envelope contract itself
    from src.eureka.universe.agent_genome import TaskEnvelope
    with pytest.raises(Exception):
        TaskEnvelope(envelope_id="E", work_id=WORK, problem_id=PROBLEM, task_id="T", agent_id="A",
                     genome_hash="0" * 8, authorized_inputs=["*"])


def test_15_output_contract_is_narrow():
    proposal = _propose()
    schema = proposal.output_contract
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["boundary", "target", "validation_status"]
    assert schema["properties"]["boundary"]["const"] == "precio -> demanda"
    assert schema["properties"]["target"]["const"] == "demanda"
    assert schema["properties"]["condition_inputs"]["items"]["enum"] == ["precio"]
    for forbidden in ("VALIDATED", "FROZEN", "PUBLISHED", "AUTHORIZED"):
        assert forbidden not in json.dumps(schema).upper().replace(OUTPUT_STATUS_CANDIDATE, "")
    assert "freeze" not in json.dumps(schema).lower()
    assert "publish" not in json.dumps(schema).lower()


def test_16_dependencies_are_valid():
    existing = _agent_record(predicate="otro")
    canonical = _canonical(agents=[existing])
    _, _, _, evaluation, candidate = _necessary(canonical)
    assert existing.genome.agent_id == "PRED-SEG-otro-Europa"
    # default: NO dependency is invented
    default = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                  now=FIXED)
    assert default.genome.dependencies == [] and default.dependencies == []
    # an explicit dependency on an EXISTING, same-work agent is accepted
    with_dep = _designer().propose(
        evaluation, candidate=candidate, canonical_state=canonical, now=FIXED,
        request=GenomeDesignRequest(requested_dependencies=["PRED-SEG-otro-Europa"]))
    assert with_dep.status is GenomeProposalStatus.PROPOSED
    assert [d.agent_id for d in with_dep.genome.dependencies] == ["PRED-SEG-otro-Europa"]
    assert with_dep.genome.dependencies[0].kind is AgentDependencyKind.DATA
    # a dependency on a NON-EXISTENT agent is refused (and never creates a registry entry)
    missing = _designer().propose(
        evaluation, candidate=candidate, canonical_state=canonical, now=FIXED,
        request=GenomeDesignRequest(requested_dependencies=["DESC-SEG-inventado-Europa"]))
    assert missing.status is GenomeProposalStatus.REJECTED
    assert missing.rejections[0].reason_code == GENOME_DEPENDENCY_UNRESOLVABLE
    assert AgentRegistry.rebuild_from(canonical).count() == 1          # unchanged


def test_17_dependency_cycle_is_rejected():
    cyclic = _agent_record(predicate="otro", dependencies=(NEW_AGENT_ID,))
    canonical = _canonical(agents=[cyclic])
    _, _, _, evaluation, candidate = _necessary(canonical)
    proposal = _designer().propose(
        evaluation, candidate=candidate, canonical_state=canonical, now=FIXED,
        request=GenomeDesignRequest(requested_dependencies=["PRED-SEG-otro-Europa"]))
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.rejections[0].reason_code == GENOME_DEPENDENCY_CYCLE


def test_18_cross_work_is_rejected():
    canonical = _canonical()                                   # work WORK-L6
    foreign = _synthetic_necessary(work_id="WORK-OTHER")       # verdict from another work
    proposal = _designer().propose(foreign, canonical_state=canonical, now=FIXED)
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.rejections[0].reason_code == GENOME_CROSS_WORK


def test_19_cross_problem_is_rejected():
    canonical = _canonical()                                   # problem PROB-L6
    foreign = _synthetic_necessary(problem_id="PROB-OTHER")    # verdict from another problem
    proposal = _designer().propose(foreign, canonical_state=canonical, now=FIXED)
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.rejections[0].reason_code == GENOME_CROSS_PROBLEM


def test_20_frozen_genome_is_immutable():
    proposal = _propose()
    genome = proposal.genome
    genome.freeze()
    assert genome.frozen is True
    mutated = genome.model_copy(deep=True)
    mutated.objective = "a different objective"
    with pytest.raises(AgentContractError) as err:
        genome.assert_compatible_with(mutated)
    assert err.value.reason_code == "FROZEN_GENOME_MUTATION"
    # the freeze flag is metadata, NOT content identity (identical hash with/without it)
    unfrozen = genome.model_copy(deep=True)
    unfrozen.frozen = False
    assert unfrozen.hash() == genome.hash()
    # while a CONTENT change does change the hash (tamper evidence works)
    assert mutated.hash() != genome.hash()


def test_21_serialization_is_deterministic():
    canonical, _, _, evaluation, candidate = _necessary()
    first = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED)
    second = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.genome.model_dump(mode="json") == second.genome.model_dump(mode="json")


def test_22_same_candidate_produces_same_genome_semantics():
    canonical, _, _, evaluation, candidate = _necessary()
    a = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED)
    b = AgentGenomeDesigner(_reg()).propose(evaluation, candidate=candidate,
                                            canonical_state=canonical, now="2026-10-01T00:00:00+00:00")
    assert a.semantic_identity() == b.semantic_identity()
    assert a.agent_id() == b.agent_id()
    assert a.proposal_id == b.proposal_id                    # identity is not the timestamp


def test_23_different_candidate_produces_different_semantic_identity():
    other = _canonical(variables=("precio", "oferta"), relationships=("precio -> oferta",))
    _, _, _, evaluation, candidate = _necessary(other)
    proposal = _designer().propose(evaluation, candidate=candidate, canonical_state=other, now=FIXED)
    assert proposal.status is GenomeProposalStatus.PROPOSED
    assert proposal.agent_id() == "PRED-SEG-oferta-Europa"
    assert proposal.agent_id() != NEW_AGENT_ID
    assert proposal.semantic_identity()["predicate"] != "demanda"
    # a different CONTEXT also yields a different identity
    third = _canonical(context="Asia")
    _, _, _, evaluation3, candidate3 = _necessary(third)
    proposal3 = _designer().propose(evaluation3, candidate=candidate3, canonical_state=third,
                                    now=FIXED)
    assert proposal3.agent_id() == "PRED-SEG-demanda-Asia"
    assert proposal3.agent_id() != NEW_AGENT_ID


# ============================================================================================= #
# 24-31. NON-MUTATION, PERSISTENCE, IDENTITY
# ============================================================================================= #
def test_24_no_registry_mutation():
    canonical, _, _, evaluation, candidate = _necessary()
    before = canonical.agent_network.model_dump(mode="json")
    before_count = AgentRegistry.rebuild_from(canonical).count()
    proposal = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                   now=FIXED)
    assert proposal.registers_agents is False and proposal.activates_agents is False
    assert canonical.agent_network.model_dump(mode="json") == before
    assert AgentRegistry.rebuild_from(canonical).count() == before_count == 0
    source = open(_MODULE_PATH, encoding="utf-8").read()
    for banned in (".register(", ".activate(", ".supersede(", ".retire(", ".complete(", ".pause("):
        assert banned not in source, banned


def test_25_no_agentruntime_invocation():
    assert "executes_agents" in AgentGenomeProposal.model_fields
    assert AgentGenomeProposal.model_fields["executes_agents"].default is False
    assert "execution_id" not in AgentGenomeProposal.model_fields
    proposal = _propose()
    assert proposal.executes_agents is False
    tree = ast.parse(open(_MODULE_PATH, encoding="utf-8").read())
    calls = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not (calls & {"execute", "run", "invoke", "activate", "register", "persist"})


def test_26_no_model_call():
    tree = ast.parse(open(_MODULE_PATH, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for banned_module in ("requests", "httpx", "socket", "urllib", "http", "openai",
                          "eureka.universe.ollama_provider",
                          "eureka.universe.provider_backed_cognitive_engine"):
        assert not any(m.startswith(banned_module) for m in imported), banned_module
    source = open(_MODULE_PATH, encoding="utf-8").read()
    for banned in ("requests.", "urlopen", "socket.", "http://", "https://", "DeepSeekModelProvider",
                   "OllamaModelProvider", "DEEPSEEK_API_KEY"):
        assert banned not in source, banned
    # the designer needs no provider and no runtime: the whole flow runs on deterministic Python
    proposal = _propose()
    assert proposal.status is GenomeProposalStatus.PROPOSED
    assert proposal.selects_provider is False


def test_27_task_network_is_unchanged():
    canonical, _, _, evaluation, candidate = _necessary()
    before = canonical.problem.structured_problem.task_network.model_dump(mode="json")
    _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED)
    assert canonical.problem.structured_problem.task_network.model_dump(mode="json") == before
    assert "modify_task_network" in json.dumps(_propose().genome.forbidden_operations)


def test_28_canonical_problem_is_unchanged():
    canonical, _, _, evaluation, candidate = _necessary()
    before = canonical.problem.model_dump(mode="json")
    fingerprint_before = canonical_state_fingerprint(canonical)
    proposal = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                   now=FIXED)
    assert canonical.problem.model_dump(mode="json") == before
    assert canonical_state_fingerprint(canonical) == fingerprint_before
    # persisting the proposal does not change the canonical content identity either
    canonical.agent_genome_proposals.append(proposal)
    assert canonical_state_fingerprint(canonical) == fingerprint_before
    stripped = canonical.model_dump(mode="json")
    stripped.pop("agent_genome_proposals")
    assert canonical_state_fingerprint(CanonicalWorkState.model_validate(stripped)) == fingerprint_before


def test_29_live_data_is_unchanged():
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
        assert state.agent_genome_proposals == []              # legacy work: no proposal, unchanged
        compared += 1
    assert compared > 0


def test_30_workstore_round_trip():
    canonical, _, _, evaluation, candidate = _necessary()
    canonical.problem_compilation, canonical.agent_necessity = _pipeline(canonical)
    proposal = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                   now=FIXED)
    canonical.agent_genome_proposals.append(proposal)
    with tempfile.TemporaryDirectory() as tmp:
        WorkStore(storage_dir=tmp)[canonical.work.work_id] = canonical
        reloaded = WorkStore(storage_dir=tmp)[canonical.work.work_id]
    assert len(reloaded.agent_genome_proposals) == 1
    assert reloaded.agent_genome_proposals[0].model_dump(mode="json") == \
        proposal.model_dump(mode="json")
    assert reloaded.agent_genome_proposals[0].genome.authority_scope == "PROPOSER"


def test_31_restart_reload_proposal_is_identical():
    canonical, _, _, evaluation, candidate = _necessary()
    canonical.problem_compilation, canonical.agent_necessity = _pipeline(canonical)
    canonical.agent_genome_proposals.append(
        _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED))
    with tempfile.TemporaryDirectory() as tmp:
        WorkStore(storage_dir=tmp)[canonical.work.work_id] = canonical
        restarted = WorkStore(storage_dir=tmp)[canonical.work.work_id]
        redesigned = _designer().propose(
            evaluation, candidate=candidate, canonical_state=restarted, now=FIXED)
    assert restarted.agent_genome_proposals[0].semantic_identity() == redesigned.semantic_identity()
    assert restarted.agent_genome_proposals[0].agent_id() == NEW_AGENT_ID


# ============================================================================================= #
# 32-35 + ATTACK MATRIX A-M
# ============================================================================================= #
def test_32_adversarial_authority_escalation_is_rejected():
    with pytest.raises(GenomeProposalError) as err:
        _designer().propose(_synthetic_necessary(), canonical_state=_canonical(),
                            request={"authority_scope": "OWNER"})
    assert err.value.reason_code == GENOME_AUTHORITY_ESCALATION
    with pytest.raises(GenomeProposalError):
        _designer().propose(_synthetic_necessary(), canonical_state=_canonical(),
                            request={"cognitive_family": "PRESCRIPTOR"})
    with pytest.raises(GenomeProposalError):
        _designer().propose(_synthetic_necessary(), canonical_state=_canonical(),
                            request={"agent_id": "PRESC-SEG-x-Y"})
    # ATTACK A: a NECESSARY verdict whose responsibility is ALREADY covered by an existing task
    covered = _canonical(tasks=[_task(description="Forecast demand", outputs=("demanda",))])
    proposal = _designer().propose(_synthetic_necessary(), canonical_state=covered, now=FIXED)
    assert proposal.status is GenomeProposalStatus.REJECTED
    assert proposal.rejections[0].reason_code == GENOME_DUPLICATES_EXISTING


def test_33_adversarial_provider_substitution_is_rejected():
    with pytest.raises(GenomeProposalError) as err:
        _designer().propose(_synthetic_necessary(), canonical_state=_canonical(),
                            request={"model": "gpt-4"})
    assert err.value.reason_code == GENOME_PROVIDER_PIN
    with pytest.raises(GenomeProposalError):
        _designer().propose(_synthetic_necessary(), canonical_state=_canonical(),
                            request={"capability_class": "LOCAL_RUNTIME"})
    from src.eureka.universe.agent_genome import ModelRequirement
    with pytest.raises(Exception):
        ModelRequirement(vendor="deepseek")


def test_34_adversarial_budget_escalation_is_rejected():
    canonical = _canonical()
    _, _, _, evaluation, candidate = _necessary(canonical)
    over = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED,
                               request=GenomeDesignRequest(requested_budget={"max_model_calls": 99}))
    assert over.status is GenomeProposalStatus.REJECTED
    assert over.rejections[0].reason_code == GENOME_BUDGET_ESCALATION
    unknown = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                  now=FIXED,
                                  request={"requested_budget": {"max_magic": 1}})
    assert unknown.status is GenomeProposalStatus.REJECTED
    assert unknown.rejections[0].reason_code == GENOME_BUDGET_ESCALATION
    # an unlimited/typo budget cannot even be expressed through the canonical contract
    with pytest.raises(Exception):
        ResourceBudget(max_model_calls=10 ** 9)


def test_35_adversarial_policy_mutation_is_rejected():
    for payload, code in (
            ({"policy": "no-gates"}, GENOME_POLICY_MUTATION),
            ({"canonical_status": "VALIDATED"}, GENOME_POLICY_MUTATION),
            ({"register": "PRED-SEG-demanda-Europa"}, GENOME_REGISTRY_REQUESTED),
            ({"activate": True}, GENOME_REGISTRY_REQUESTED),
            ({"execute": True}, GENOME_RUNTIME_REQUESTED),
            ({"runtime": "AgentRuntime"}, GENOME_RUNTIME_REQUESTED),
            ({"task_network": "new"}, GENOME_TASKNETWORK_MUTATION_REQUESTED),
            ({"next_owner": "EM Publisher"}, GENOME_TASKNETWORK_MUTATION_REQUESTED)):
        with pytest.raises(GenomeProposalError) as err:
            _designer().propose(_synthetic_necessary(), canonical_state=_canonical(),
                                request=payload)
        assert err.value.reason_code == code, payload


def test_attack_matrix_b_to_m_each_fails_closed():
    """Attacks B..M: router / validator / publisher / provider / budget / evidence / cross ids /
    TaskNetwork / canonical mutation / registry / runtime."""
    canonical = _canonical()
    _, _, _, evaluation, candidate = _necessary(canonical)
    designer = _designer()

    # B/C/D: router / validator / publisher ambitions live in the genome declaration itself
    proposal = designer.propose(evaluation, candidate=candidate, canonical_state=canonical,
                                now=FIXED)
    for forbidden in ("route_next_owner", "validate_own_output", "publish_any_artifact"):
        assert forbidden in proposal.genome.forbidden_operations
    assert proposal.genome.execution_level == "COGNITIVE"          # never SYSTEM/HUMAN

    # E provider substitution / F unlimited budget / G fake evidence / H-I cross ids
    for payload, code in (({"provider": "x"}, GENOME_PROVIDER_PIN),
                          ({"register": True}, GENOME_REGISTRY_REQUESTED)):
        with pytest.raises(GenomeProposalError) as err:
            designer.propose(evaluation, candidate=candidate, canonical_state=canonical,
                             request=payload)
        assert err.value.reason_code == code
    # an escalated budget is refused as a REJECTED proposal (a request field, not a smuggling key)
    over = designer.propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED,
                            request={"requested_budget": {"max_tokens": 10 ** 7}})
    assert over.status is GenomeProposalStatus.REJECTED
    assert over.rejections[0].reason_code == GENOME_BUDGET_ESCALATION
    fake = evaluation.model_copy(update={"evidence_refs": ["EVI-FAKE"]})
    assert designer.propose(fake, candidate=candidate, canonical_state=canonical, now=FIXED) \
        .rejections[0].reason_code == GENOME_EVIDENCE_FABRICATED
    cross_work = evaluation.model_copy(update={"work_id": "WORK-OTHER"})
    assert designer.propose(cross_work, candidate=candidate, canonical_state=canonical, now=FIXED) \
        .rejections[0].reason_code == GENOME_CROSS_WORK
    cross_problem = evaluation.model_copy(update={"problem_id": "PROB-OTHER"})
    assert designer.propose(cross_problem, candidate=candidate, canonical_state=canonical,
                            now=FIXED).rejections[0].reason_code == GENOME_CROSS_PROBLEM

    # J/K: TaskNetwork and canonical problem are untouched by any of the above
    before_network = canonical.problem.structured_problem.task_network.model_dump(mode="json")
    before_problem = canonical.problem.model_dump(mode="json")
    designer.propose(evaluation, candidate=candidate, canonical_state=canonical, now=FIXED)
    assert canonical.problem.structured_problem.task_network.model_dump(mode="json") == before_network
    assert canonical.problem.model_dump(mode="json") == before_problem

    # L/M: registry and runtime are unreachable (structural + behavioural)
    assert canonical.agent_network.records == []
    assert "register_any_agent" in FORBIDDEN_OPERATIONS


def test_f11_assessment_hash_includes_created_at():
    """F11 (assessed, NOT repaired in LOOP 6): the genome hash is time-dependent.

    This is pinned deterministically (no flakiness): two genomes whose ONLY difference is
    ``created_at`` hash differently, which is what makes AgentRegistry's idempotency clock-dependent.
    """
    canonical, _, _, evaluation, candidate = _necessary()
    proposal = _designer().propose(evaluation, candidate=candidate, canonical_state=canonical,
                                   now=FIXED)
    genome = proposal.genome
    other = genome.model_copy(deep=True)
    other.created_at = "2027-01-01T00:00:00+00:00"
    assert genome.hash() != other.hash(), "F11 changed: hash no longer includes created_at"
    assert "created_at" in genome.model_dump(mode="json")
    # everything EXCEPT the volatile timestamp is identical
    assert {k: v for k, v in genome.model_dump(mode="json").items() if k != "created_at"} == \
        {k: v for k, v in other.model_dump(mode="json").items() if k != "created_at"}


# ============================================================================================= #
# LOCAL E2E through the REAL orchestrator (no model call)
# ============================================================================================= #
E2E_INTENT = "LOOP6 E2E: analizar el impacto del precio en la demanda en Europa y decidir el plan"


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


def test_e2e_real_pipeline_produces_a_candidate_genome_proposal():
    canonical = _e2e_orchestrator().orchestrate(E2E_INTENT)
    proposals = canonical.agent_genome_proposals
    assert len(proposals) == 1                                  # exactly the NECESSARY verdict
    proposal = proposals[0]
    assert proposal.status is GenomeProposalStatus.PROPOSED
    assert proposal.necessity_decision == "NECESSARY"
    assert proposal.necessity_reason_code == "NECESSARY_EMERGENT_UNIT_JUSTIFIED"
    assert proposal.boundary == "precio -> demanda"
    assert proposal.agent_id() == NEW_AGENT_ID
    assert proposal.genome.authority_scope == "PROPOSER"
    assert proposal.genome.identity.cognitive_family is CognitiveFamily.PREDICTOR
    assert proposal.genome.identity.network_role is NetworkRole.SEGREGATOR
    assert proposal.genome.return_to == "EM Predictor"
    assert proposal.output_contract["properties"]["validation_status"]["const"] == "CANDIDATE"
    assert proposal.provider_selection == PROVIDER_SELECTION_DEFERRED

    # the real pipeline proves the proposal pipeline STOPS here
    assert canonical.agent_network.records == []                 # no registration
    assert canonical.agent_network.executions == []              # no execution
    assert len(canonical.problem.structured_problem.task_network.tasks) == 4   # untouched
    assert proposal.input_contract.authorized_inputs == ["precio", "demanda"]
    assert proposal.input_contract.authorized_evidence_ids == []

    # canonical identity is unaffected by the proposal
    stripped = canonical.model_dump(mode="json")
    stripped.pop("agent_genome_proposals")
    assert canonical_state_fingerprint(CanonicalWorkState.model_validate(stripped)) == \
        canonical_state_fingerprint(canonical)

    # deterministic across runs: the COGNITIVE identity is identical (per-work identity differs)
    cognitive = lambda p: {k: v for k, v in p.semantic_identity().items()
                           if k not in ("work_id", "problem_id")}
    again = _e2e_orchestrator().orchestrate(E2E_INTENT)
    assert cognitive(again.agent_genome_proposals[0]) == cognitive(proposal)
    assert again.agent_genome_proposals[0].agent_id() == NEW_AGENT_ID
