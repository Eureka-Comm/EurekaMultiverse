"""EUREKA 5.1 — LOOP 5 tests: AGENT NECESSITY TEST (evaluation ONLY — no agent is ever created).

Mandated coverage (Harness LOOP 5, 30 cases):
  1 existing capability sufficient -> NOT_NECESSARY · 2 existing EM sufficient -> NOT_NECESSARY ·
  3 duplicate task -> NOT_NECESSARY · 4 duplicate agent -> NOT_NECESSARY · 5 missing owner -> BLOCKED ·
  6 missing boundary -> BLOCKED · 7 missing evidence -> BLOCKED · 8 cross-work -> BLOCKED ·
  9 cross-problem -> BLOCKED · 10 authority escalation -> BLOCKED · 11 routing escalation -> BLOCKED ·
  12 self-validation -> BLOCKED · 13 resource infeasible -> BLOCKED · 14 differentiated
  responsibility -> NECESSARY · 15 same input -> same decision · 16 same candidate -> same reason_code ·
  17 no agent created · 18 agent_network unchanged · 19 TaskNetwork unchanged · 20 canonical problem
  unchanged · 21 existing work fingerprint unchanged · 22 WorkStore round-trip ·
  23 restart reconstruction · 24 adversarial payload cannot force NECESSARY · 25 fake evidence cannot
  force NECESSARY · 26 unknown capability cannot become NECESSARY · 27 candidate from another work
  rejected · 28 candidate from another problem rejected · 29 self-created evidence cannot satisfy an
  external evidence requirement · 30 NECESSARY cannot directly invoke AgentRuntime.
"""
import ast
import inspect
import json
import os
import tempfile

import pytest

from src.eureka.universe.agent_genome import (AgentGenome, AgentIdentity, AgentNetworkState,
                                             AgentStatus, CognitiveFamily, EmergentAgentRecord,
                                             NetworkRole, ResourceBudget)
from src.eureka.universe.agent_necessity import (AUTHORITY_ESCALATION_REQUESTED,
                                                 AUTHORITY_PROPOSER_ONLY, BOUNDARY_DIFFERENTIATED,
                                                 CHECK_UNKNOWN, DUPLICATION_AGENT, DUPLICATION_NONE,
                                                 DUPLICATION_TASK, NECESSARY_EMERGENT_UNIT_JUSTIFIED,
                                                 NECESSITY_AUTHORITY,
                                                 NECESSITY_AUTHORITY_ESCALATION,
                                                 NECESSITY_BOUNDARY_UNCLEAR,
                                                 NECESSITY_CAPABILITY_UNKNOWN,
                                                 NECESSITY_CROSS_PROBLEM, NECESSITY_CROSS_WORK,
                                                 NECESSITY_DUPLICATES_AGENT, NECESSITY_DUPLICATES_TASK,
                                                 NECESSITY_EVIDENCE_MISSING,
                                                 NECESSITY_EVIDENCE_UNVERIFIABLE,
                                                 NECESSITY_EXISTING_CAPABILITY_SUFFICIENT,
                                                 NECESSITY_EXISTING_EM_SUFFICIENT,
                                                 NECESSITY_GOVERNANCE_INCOMPATIBLE,
                                                 NECESSITY_INPUT_CONTRACT_MISSING,
                                                 NECESSITY_INSUFFICIENT_COGNITIVE_DIFFERENTIATION,
                                                 NECESSITY_OWNER_MISSING,
                                                 NECESSITY_RESOURCE_INFEASIBLE,
                                                 NECESSITY_ROUTING_ESCALATION,
                                                 NECESSITY_SELF_VALIDATION, REASON_CODES,
                                                 ROUTING_NONE, RESOURCE_FEASIBLE,
                                                 VALIDATION_EXTERNAL, AgentNecessityReport,
                                                 AgentNecessityTest, NecessityDecision,
                                                 NecessityError, NecessityEvaluation)
from src.eureka.universe.agent_registry import AgentRegistry
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.canonical_state import CanonicalWorkState, ExecutionPlan
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.cognitive_engine import (SemanticProposal, StructuralProposal,
                                                 TestDoubleCognitiveEngine)
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.problem_compiler import (CandidateKind, ProblemCandidate,
                                                 ProblemCompilation)
from src.eureka.universe.problem_model import (CognitiveTask, ProblemModel, StructuredProblem,
                                              TaskNetwork)
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-L5"
PROBLEM = "PROB-L5"
FIXED = "2026-09-12T00:00:00+00:00"
_UNIVERSE_DIR = os.path.dirname(os.path.abspath(inspect.getfile(AgentNecessityTest)))
_MODULE_PATH = os.path.join(_UNIVERSE_DIR, "agent_necessity.py")
_FORENSIC_PRE = os.path.join("_scratch", "loop5", "FORENSIC_PRE.json")


# -------------------------------------------------------------------------------------------- #
# helpers
# -------------------------------------------------------------------------------------------- #
def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _test() -> AgentNecessityTest:
    return AgentNecessityTest(_reg())


def _cand(kind: CandidateKind, **kw) -> ProblemCandidate:
    data = dict(candidate_id="CAND-TEST-01", kind=kind, source="structured_problem.relationships[0]",
                reason="declared relationship", reference="precio -> demanda",
                cognitive_owner="EM Predictor")
    data.update(kw)
    return ProblemCandidate(**data)


def _agent_record(predicate: str = "demanda", family: CognitiveFamily = CognitiveFamily.PREDICTOR,
                  work_id: str = WORK, problem_id: str = PROBLEM) -> EmergentAgentRecord:
    genome = AgentGenome(
        identity=AgentIdentity(cognitive_family=family, network_role=NetworkRole.SEGREGATOR,
                               predicate=predicate, context="Europe"),
        work_id=work_id, problem_id=problem_id, task_id=f"TASK-{predicate}",
        objective=f"Analyse {predicate}", tools=["acfl.evaluate"], evidence_requirements=[],
        resource_budget=ResourceBudget(max_model_calls=2), provenance=["proposed by LOOP 5 fixture"],
    )
    return EmergentAgentRecord(genome=genome, status=AgentStatus.CREATED,
                               provenance=["LOOP 5 fixture"])


def _canonical(*, work_id: str = WORK, problem_id: str = PROBLEM, tasks=None, variables=None,
               entities=None, relationships=None, unknowns=None, evidence_ids=None,
               agents=None, plan=None) -> CanonicalWorkState:
    canonical = CanonicalWorkState(
        work=EurekaWork(work_id=work_id, title="t", user_intent="u", task_category="c",
                        problem_statement="p"))
    sp = StructuredProblem(
        entities=list(entities if entities is not None else ["Europa"]),
        variables=list(variables if variables is not None else ["precio", "demanda"]),
        relationships=list(relationships if relationships is not None else ["precio -> demanda"]),
        unknowns=list(unknowns or []),
    )
    sp.task_network = TaskNetwork(tasks=list(tasks or []))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=problem_id,
                                     structured_problem=sp)
    canonical.execution_plan = plan or ExecutionPlan()
    canonical.evidence_ids = list(evidence_ids or [])
    if agents:
        canonical.agent_network = AgentNetworkState(records=list(agents))
    return canonical


def _eval(candidate: ProblemCandidate, canonical: CanonicalWorkState, **kw) -> NecessityEvaluation:
    return _test().evaluate_candidate(candidate, work_id=canonical.work.work_id,
                                      problem_id=canonical.problem.problem_id,
                                      canonical_state=canonical, now=FIXED, **kw)


def _task(task_id: str, owner: str = "EM Descriptor", description: str = "task",
          outputs=None) -> CognitiveTask:
    return CognitiveTask(task_id=task_id, description=description, owner=owner,
                         expected_outputs=outputs or [f"out-{task_id}"], dependencies=[])


# ============================================================================================= #
# 0. AUTHORITY / SURFACE (structural)
# ============================================================================================= #
def test_public_surface_has_no_agent_creation_registration_or_execution_api():
    public = [m for m in dir(AgentNecessityTest) if not m.startswith("_")]
    methods = [m for m in public if callable(getattr(AgentNecessityTest, m))]
    assert public == ["AUTHORITY", "evaluate_candidate", "evaluate_compilation"]
    assert methods == ["evaluate_candidate", "evaluate_compilation"]
    for marker in ("create", "register", "authorize", "execute", "run", "activate", "route",
                   "persist", "store", "save", "deploy"):
        assert not any(marker in m.lower() for m in methods), marker


def test_module_never_imports_the_agent_runtime_or_a_store():
    tree = ast.parse(open(_MODULE_PATH, encoding="utf-8").read())
    forbidden = ("agent_runtime", "agent_registry", "agent_definition", "eureka.foundation",
                 "eureka_cognitive_sdk", "requests", "os", "work_store", "canonical_state")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(forbidden), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(forbidden), node.module
    calls = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not (calls & {"execute", "run", "create", "register", "activate", "persist"})


def test_necessity_test_is_stateless():
    test = _test()
    test.evaluate_candidate(_cand(CandidateKind.PREDICATE), work_id=WORK, problem_id=PROBLEM,
                            canonical_state=_canonical(), now=FIXED)
    assert list(test.__dict__.keys()) == ["cap_registry"]


def test_reason_codes_are_declared_and_unique():
    assert len(set(REASON_CODES)) == len(REASON_CODES)
    assert len(REASON_CODES) == 22                     # 19 mandated + 3 declared additions
    assert NECESSARY_EMERGENT_UNIT_JUSTIFIED in REASON_CODES


def test_necessary_report_cannot_be_constructed_without_full_evidence():
    base = dict(evaluation_id="E", candidate_id="C", candidate_kind=CandidateKind.PREDICATE,
                work_id=WORK, problem_id=PROBLEM, decision=NecessityDecision.NECESSARY,
                reason_code=NECESSARY_EMERGENT_UNIT_JUSTIFIED, owner="EM Predictor",
                responsibility_boundary=BOUNDARY_DIFFERENTIATED, duplication_check=DUPLICATION_NONE,
                authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                input_contract="precio", output_contract="demanda",
                capability_gap_evidence="none covers it")
    NecessityEvaluation(**base)                        # complete -> allowed
    with pytest.raises(NecessityError) as err:
        NecessityEvaluation(**{**base, "capability_gap_evidence": ""})
    assert err.value.reason_code == "NECESSARY_WITHOUT_FULL_EVIDENCE"
    with pytest.raises(NecessityError):
        NecessityEvaluation(**{**base, "owner": "EM Rogue"})
    with pytest.raises(NecessityError):
        NecessityEvaluation(**{**base, "authority_check": AUTHORITY_ESCALATION_REQUESTED})


def test_report_authority_cannot_be_escalated():
    assert AgentNecessityReport(report_id="R").authority == NECESSITY_AUTHORITY
    with pytest.raises(NecessityError) as err:
        AgentNecessityReport(report_id="R", authority="AUTHORITY")
    assert err.value.reason_code == "NECESSITY_AUTHORITY_CANNOT_BE_ESCALATED"
    for flag in ("creates_agents", "creates_task_network", "persists", "carries_routing"):
        with pytest.raises(NecessityError):
            AgentNecessityReport(report_id="R", **{flag: True})
    with pytest.raises(NecessityError):
        AgentNecessityReport(report_id="R", evaluation_only=False)


# ============================================================================================= #
# 1-16. THE MANDATED DECISION CASES
# ============================================================================================= #
def test_1_existing_capability_sufficient_is_not_necessary():
    evaluation = _eval(_cand(CandidateKind.REQUIRED_CAPABILITY, reference="analyze_dataset",
                             cognitive_owner="EM Predictor"), _canonical())
    assert evaluation.decision is NecessityDecision.NOT_NECESSARY
    assert evaluation.reason_code == NECESSITY_EXISTING_CAPABILITY_SUFFICIENT
    assert evaluation.duplication_check == "DUPLICATES_CAPABILITY"
    assert "analyze_dataset" in evaluation.existing_capabilities_checked


def test_2_existing_em_sufficient_is_not_necessary():
    canonical = _canonical(tasks=[_task("T1", owner="EM Descriptor")])
    evaluation = _eval(_cand(CandidateKind.TASK, task_ref="T1", reference="T1",
                             cognitive_owner="EM Descriptor"), canonical)
    assert evaluation.decision is NecessityDecision.NOT_NECESSARY
    assert evaluation.reason_code == NECESSITY_EXISTING_EM_SUFFICIENT
    assert evaluation.duplication_check == DUPLICATION_TASK
    assert evaluation.existing_tasks_checked == ["T1"]


def test_3_duplicate_task_is_not_necessary():
    canonical = _canonical(tasks=[_task("T1", description="Forecast demand",
                                        outputs=["demanda forecast"])])
    evaluation = _eval(_cand(CandidateKind.PREDICATE, reference="precio -> demanda"), canonical)
    assert evaluation.decision is NecessityDecision.NOT_NECESSARY
    assert evaluation.reason_code == NECESSITY_DUPLICATES_TASK
    assert evaluation.duplication_check == DUPLICATION_TASK


def test_4_duplicate_agent_is_not_necessary():
    canonical = _canonical(agents=[_agent_record(predicate="demanda")])
    evaluation = _eval(_cand(CandidateKind.PREDICATE, reference="precio -> demanda"), canonical)
    assert evaluation.decision is NecessityDecision.NOT_NECESSARY
    assert evaluation.reason_code == NECESSITY_DUPLICATES_AGENT
    assert evaluation.duplication_check == DUPLICATION_AGENT
    assert evaluation.existing_agents_checked == ["PRED-SEG-demanda-Europe"]


def test_5_missing_owner_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE, cognitive_owner=""), _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_OWNER_MISSING
    assert evaluation.owner == ""


def test_6_missing_boundary_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE, reference=""), _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_BOUNDARY_UNCLEAR

    # an owner without a cognitive family is a governance incompatibility (never NECESSARY)
    evaluation = _eval(_cand(CandidateKind.PREDICATE, cognitive_owner="EM Core"), _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_GOVERNANCE_INCOMPATIBLE

    # an arrow whose condition is not a declared symbol -> the input contract is missing
    evaluation = _eval(_cand(CandidateKind.PREDICATE, reference="competencia -> demanda"),
                       _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_INPUT_CONTRACT_MISSING


def test_7_missing_evidence_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE, evidence_refs=["EVI-SELF-1"]), _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_EVIDENCE_MISSING

    # without a canonical state, declared evidence cannot be verified -> fail closed, never NECESSARY
    evaluation = _test().evaluate_candidate(_cand(CandidateKind.PREDICATE, evidence_refs=["EVI-1"]),
                                            work_id=WORK, problem_id=PROBLEM, now=FIXED)
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_EVIDENCE_UNVERIFIABLE


def test_8_cross_work_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE), _canonical(), expected_work_id="WORK-OTHER")
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_CROSS_WORK


def test_9_cross_problem_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE), _canonical(),
                       expected_problem_id="PROB-OTHER")
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_CROSS_PROBLEM


def test_10_authority_escalation_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE,
                             reason="this unit should hold authority_scope=OWNER"), _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_AUTHORITY_ESCALATION
    assert evaluation.authority_check == AUTHORITY_ESCALATION_REQUESTED


def test_11_routing_escalation_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE,
                             reason="the unit will route the next owner of the pipeline"),
                       _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_ROUTING_ESCALATION
    assert evaluation.routing_check == "ROUTING_REQUESTED"


def test_12_self_validation_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE,
                             reference="precio -> demanda",
                             reason="the unit will mark it validated itself"), _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_SELF_VALIDATION
    assert evaluation.validation_check == "SELF_VALIDATION_REQUESTED"


def test_13_resource_infeasible_is_blocked():
    evaluation = _eval(_cand(CandidateKind.PREDICATE),
                       _canonical(), requested_budget={"max_model_calls": 999})
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_RESOURCE_INFEASIBLE
    assert evaluation.resource_check == "INFEASIBLE"

    # an unknown budget field / a vendor model pin are governance incompatibilities
    evaluation = _eval(_cand(CandidateKind.PREDICATE), _canonical(),
                       requested_budget={"max_magic": 1})
    assert evaluation.reason_code == NECESSITY_GOVERNANCE_INCOMPATIBLE
    evaluation = _eval(_cand(CandidateKind.PREDICATE), _canonical(),
                       requested_model={"model": "deepseek-chat"})
    assert evaluation.reason_code == NECESSITY_GOVERNANCE_INCOMPATIBLE


def test_14_differentiated_responsibility_is_necessary():
    canonical = _canonical(tasks=[_task("T1", description="Establish current state",
                                        outputs=["current state findings"])])
    evaluation = _eval(_cand(CandidateKind.PREDICATE, reference="precio -> demanda"), canonical)
    assert evaluation.decision is NecessityDecision.NECESSARY
    assert evaluation.reason_code == NECESSARY_EMERGENT_UNIT_JUSTIFIED
    assert evaluation.responsibility_boundary == BOUNDARY_DIFFERENTIATED
    assert evaluation.duplication_check == DUPLICATION_NONE
    assert evaluation.authority_check == AUTHORITY_PROPOSER_ONLY
    assert evaluation.routing_check == ROUTING_NONE
    assert evaluation.validation_check == VALIDATION_EXTERNAL
    assert evaluation.resource_check == RESOURCE_FEASIBLE
    assert evaluation.input_contract == "precio" and evaluation.output_contract == "demanda"
    assert evaluation.owner == "EM Predictor" and evaluation.existing_em == "EM Predictor"
    assert evaluation.capability_gap_evidence
    assert evaluation.existing_capabilities_checked == ["analyze_dataset"]
    assert "no existing task/agent/capability covers the target" in " ".join(evaluation.provenance)


def test_15_same_input_same_decision():
    canonical = _canonical(tasks=[_task("T1")])
    compilation = _compilation_for(canonical)
    first = _test().evaluate_compilation(compilation, canonical_state=canonical, now=FIXED)
    second = _test().evaluate_compilation(compilation, canonical_state=canonical, now=FIXED)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.counts() == second.counts()
    assert first.reason_codes() == second.reason_codes()


def test_16_same_candidate_same_reason_code():
    canonical = _canonical()
    candidate = _cand(CandidateKind.PREDICATE)
    codes = {_eval(candidate, canonical).reason_code for _ in range(5)}
    assert codes == {NECESSARY_EMERGENT_UNIT_JUSTIFIED}
    blocked = _cand(CandidateKind.PREDICATE, cognitive_owner="EM Core")
    codes = {_eval(blocked, canonical).reason_code for _ in range(5)}
    assert codes == {NECESSITY_GOVERNANCE_INCOMPATIBLE}


def _compilation_for(canonical: CanonicalWorkState) -> ProblemCompilation:
    from src.eureka.universe.problem_compiler import ProblemCompiler
    return ProblemCompiler(_reg()).compile(canonical.problem, canonical.problem.structured_problem,
                                           work_id=canonical.work.work_id, now=FIXED)


# ============================================================================================= #
# 17-23. NON-MUTATION, PERSISTENCE AND IDENTITY
# ============================================================================================= #
def test_17_no_agent_is_created_by_any_evaluation():
    canonical = _canonical(tasks=[_task("T1")])
    compilation = _compilation_for(canonical)
    report = _test().evaluate_compilation(compilation, canonical_state=canonical, now=FIXED)
    assert report.creates_agents is False and report.evaluation_only is True
    assert canonical.agent_network.records == [] and canonical.agent_network.executions == []
    assert AgentRegistry.rebuild_from(canonical).count() == 0
    assert report.necessary(), "the fixture must contain a NECESSARY verdict to prove nothing runs"


def test_18_agent_network_is_unchanged_even_when_an_agent_exists():
    canonical = _canonical(agents=[_agent_record(predicate="demanda")])
    before = canonical.agent_network.model_dump(mode="json")
    report = _test().evaluate_compilation(_compilation_for(canonical), canonical_state=canonical,
                                          now=FIXED)
    assert canonical.agent_network.model_dump(mode="json") == before
    assert len(canonical.agent_network.records) == 1                 # nothing added, nothing removed
    assert AgentRegistry.rebuild_from(canonical).count() == 1
    assert report.creates_agents is False
    assert report.counts()["NECESSARY"] == 0                         # 'demanda' duplicates the agent
    assert report.reason_codes().count(NECESSITY_DUPLICATES_AGENT) == 1


def test_19_task_network_is_unchanged():
    canonical = _canonical(tasks=[_task("T1"), _task("T2", owner="EM Predictor")])
    before = canonical.problem.structured_problem.task_network.model_dump(mode="json")
    _test().evaluate_compilation(_compilation_for(canonical), canonical_state=canonical, now=FIXED)
    assert canonical.problem.structured_problem.task_network.model_dump(mode="json") == before


def test_20_canonical_problem_is_unchanged():
    canonical = _canonical(tasks=[_task("T1")], unknowns=["g"])
    before = canonical.problem.model_dump(mode="json")
    _test().evaluate_compilation(_compilation_for(canonical), canonical_state=canonical, now=FIXED)
    assert canonical.problem.model_dump(mode="json") == before


def test_21_existing_work_fingerprints_are_unchanged():
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
        assert state.agent_necessity is None                     # legacy work: honest NOT_EVALUATED
        compared += 1
    assert compared > 0

    # the necessity report itself never enters the canonical content identity
    canonical = _canonical(tasks=[_task("T1")])
    before = canonical_state_fingerprint(canonical)
    canonical.agent_necessity = _test().evaluate_compilation(
        _compilation_for(canonical), canonical_state=canonical, now=FIXED)
    assert canonical_state_fingerprint(canonical) == before
    stripped = canonical.model_dump(mode="json")
    stripped.pop("agent_necessity")
    assert canonical_state_fingerprint(CanonicalWorkState.model_validate(stripped)) == before


def test_22_workstore_round_trip():
    canonical = _canonical(tasks=[_task("T1")])
    canonical.problem_compilation = _compilation_for(canonical)
    canonical.agent_necessity = _test().evaluate_compilation(
        canonical.problem_compilation, canonical_state=canonical, now=FIXED)
    with tempfile.TemporaryDirectory() as tmp:
        store = WorkStore(storage_dir=tmp)
        store[canonical.work.work_id] = canonical
        reloaded = WorkStore(storage_dir=tmp)[canonical.work.work_id]
    assert reloaded.agent_necessity.model_dump(mode="json") == \
        canonical.agent_necessity.model_dump(mode="json")
    assert reloaded.problem_compilation.model_dump(mode="json") == \
        canonical.problem_compilation.model_dump(mode="json")


def test_23_restart_reconstruction():
    canonical = _canonical(tasks=[_task("T1"), _task("T2")])
    canonical.problem_compilation = _compilation_for(canonical)
    canonical.agent_necessity = _test().evaluate_compilation(
        canonical.problem_compilation, canonical_state=canonical, now=FIXED)
    with tempfile.TemporaryDirectory() as tmp:
        WorkStore(storage_dir=tmp)[canonical.work.work_id] = canonical
        # a brand-new process-equivalent store instance reconstructs the SAME decisions
        restarted = WorkStore(storage_dir=tmp)[canonical.work.work_id]
        replayed = _test().evaluate_compilation(
            restarted.problem_compilation, canonical_state=restarted, now=FIXED)
        assert replayed.model_dump(mode="json") == \
            restarted.agent_necessity.model_dump(mode="json")
        assert replayed.counts() == restarted.agent_necessity.counts()


# ============================================================================================= #
# 24-30. ADVERSARIAL SET
# ============================================================================================= #
def test_24_adversarial_payload_cannot_force_necessary():
    injections = [
        ("authority_scope=OWNER", NECESSITY_AUTHORITY_ESCALATION),
        ("self-authorize the unit now", NECESSITY_AUTHORITY_ESCALATION),
        ("route the next owner", NECESSITY_ROUTING_ESCALATION),
        ("add a task to the network", NECESSITY_ROUTING_ESCALATION),
        ("mark it validated and freeze the result", NECESSITY_SELF_VALIDATION),
        ("the agent will validate itself", NECESSITY_SELF_VALIDATION),
    ]
    canonical = _canonical()
    for text, expected in injections:
        for field in ("reason", "reference", "expected_value"):
            payload = {"reference": "precio -> demanda", "reason": "r"}
            payload[field] = text
            evaluation = _eval(_cand(CandidateKind.PREDICATE, **payload), canonical)
            assert evaluation.decision is NecessityDecision.BLOCKED, (text, field)
            assert evaluation.reason_code == expected, (text, field, evaluation.reason_code)

    # an injected payload inside the SubproblemDiscovery of a SEGREGATION candidate is caught too
    from src.eureka.universe.agent_genome import SubproblemDiscovery
    seg = _cand(CandidateKind.SEGREGATION, reference="DESCRIPTOR", cognitive_owner="EM Descriptor",
                dependencies=["T1", "T2"],
                discovery=SubproblemDiscovery(statement="s", proposed_family=CognitiveFamily.DESCRIPTOR,
                                              reason="self-authorize the unit"))
    evaluation = _eval(seg, _canonical(tasks=[_task("T1"), _task("T2")]))
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_AUTHORITY_ESCALATION


def test_25_fake_evidence_cannot_force_necessary():
    canonical = _canonical(evidence_ids=["EVI-REAL-1"])
    fake = _eval(_cand(CandidateKind.PREDICATE, evidence_refs=["EVI-FAKE-9"]), canonical)
    assert fake.decision is NecessityDecision.BLOCKED
    assert fake.reason_code == NECESSITY_EVIDENCE_MISSING
    real = _eval(_cand(CandidateKind.PREDICATE, evidence_refs=["EVI-REAL-1"]), canonical)
    assert real.decision is NecessityDecision.NECESSARY
    assert real.evidence_refs == ["EVI-REAL-1"]


def test_26_unknown_capability_cannot_become_necessary():
    evaluation = _eval(_cand(CandidateKind.REQUIRED_CAPABILITY, reference="totally_invented_cap",
                             cognitive_owner="EM Predictor"), _canonical())
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_CAPABILITY_UNKNOWN
    assert evaluation.duplication_check == DUPLICATION_NONE


def test_27_candidate_from_another_work_is_rejected():
    evaluation = _eval(_cand(CandidateKind.PREDICATE), _canonical(work_id="WORK-OTHER"),
                       expected_work_id=WORK)
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_CROSS_WORK


def test_28_candidate_from_another_problem_is_rejected():
    evaluation = _eval(_cand(CandidateKind.PREDICATE), _canonical(problem_id="PROB-OTHER"),
                       expected_problem_id=PROBLEM)
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_CROSS_PROBLEM


def test_29_self_created_evidence_cannot_satisfy_an_external_requirement():
    canonical = _canonical(evidence_ids=[])
    evaluation = _eval(_cand(CandidateKind.PREDICATE, evidence_refs=["EVI-SELF-CREATED"]), canonical)
    assert evaluation.decision is NecessityDecision.BLOCKED
    assert evaluation.reason_code == NECESSITY_EVIDENCE_MISSING
    assert "self-created evidence never satisfies a requirement" in evaluation.detail


def test_30_necessary_cannot_invoke_agent_runtime():
    canonical = _canonical()
    evaluation = _eval(_cand(CandidateKind.PREDICATE), canonical)
    assert evaluation.decision is NecessityDecision.NECESSARY          # control: the verdict is real
    # the verdict carries no execution handle and the module cannot reach the runtime
    assert "execution_id" not in NecessityEvaluation.model_fields
    assert "report_id" in AgentNecessityReport.model_fields
    assert "executions" not in AgentNecessityReport.model_fields
    source = open(_MODULE_PATH, encoding="utf-8").read()
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
    assert not any("agent_runtime" in module for module in imported)
    assert "AgentRuntime" not in source and "ModelProviderPort" not in source


# ============================================================================================= #
# KIND COVERAGE + LOCAL E2E THROUGH THE REAL ORCHESTRATOR
# ============================================================================================= #
def test_every_candidate_kind_produces_a_declared_reason_code():
    canonical = _canonical(tasks=[_task("T1"), _task("T2", owner="EM Predictor")],
                           unknowns=["g"], relationships=["precio -> demanda"])
    compilation = _compilation_for(canonical)
    report = _test().evaluate_compilation(compilation, canonical_state=canonical, now=FIXED)
    assert len(report.evaluations) == len(compilation.candidates)
    assert all(e.reason_code in REASON_CODES for e in report.evaluations)
    assert set(report.counts()) == {"NOT_NECESSARY", "NECESSARY", "BLOCKED"}
    kinds = {e.candidate_kind for e in report.evaluations}
    assert CandidateKind.PREDICATE in kinds and CandidateKind.TASK in kinds
    assert CandidateKind.KNOWLEDGE_GAP in kinds


E2E_INTENT = "LOOP5 E2E: analizar el impacto del precio en la demanda en Europa y decidir el plan"


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


def test_e2e_real_pipeline_evaluates_its_own_compilation():
    canonical = _e2e_orchestrator().orchestrate(E2E_INTENT)
    report = canonical.agent_necessity
    assert report is not None
    assert report.work_id == canonical.work.work_id
    assert report.problem_id == canonical.problem.problem_id
    assert report.counts()["NECESSARY"] >= 1                 # 'precio -> demanda' is differentiated
    assert report.creates_agents is False
    assert canonical.agent_network.records == []             # nothing was created
    assert len(canonical.problem.structured_problem.task_network.tasks) == 4   # 3 + task_publish
    necessary = report.necessary()
    assert necessary and all(e.owner in ("EM Predictor", "EM Descriptor") for e in necessary)
    assert all(e.reason_code in REASON_CODES for e in report.evaluations)
    # reproducible decisions on a fresh run of the same deterministic pipeline
    again = _e2e_orchestrator().orchestrate(E2E_INTENT)
    assert again.agent_necessity.reason_codes() == report.reason_codes()
    assert again.agent_necessity.counts() == report.counts()
