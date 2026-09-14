"""EUREKA 5.1 — LOOP 4 tests: PROBLEM COMPILER (compilation ENRICHMENT, never an authority).

Mandated coverage (Harness LOOP 4):
  1 simple problem · 2 composite problem · 3 multiple predicates · 4 knowledge gaps ·
  5 required capabilities · 6 task candidates · 7 segregation candidates · 8 dependencies ·
  9 uncertainties · 10 problem with no candidates · 11 duplicate candidates · 12 invalid predicate ·
  13 candidate without source · 14 candidate without ownership · 15 absent evidence ·
  16 backwards compatibility · 17 determinism/reproducibility · 18 cross-work isolation ·
  19 cross-problem isolation.

Adversarial set (every unauthorised attempt must REJECT or FAIL CLOSED):
  second TaskNetwork · second ProblemCompiler authority · routing from ProblemCompiler · direct agent
  creation · agent authorisation · authority escalation · fake evidence · fake predicate · cross-work
  contamination · cross-problem contamination · canonical-state mutation · duplicate task candidates ·
  duplicate segregation candidates · ownership spoofing.

Authority chain under test (unchanged): ProblemModel -> EM Core -> Structurer -> Orchestrator ->
TaskNetwork (ONE authority: EMStructurer); ProblemCompiler only ENRICHES it.
"""
import ast
import inspect
import json
import os

import pytest

from src.eureka.universe.agent_genome import (CONSTITUTIONAL_EM, FAMILY_OWNER, AgentNetworkState,
                                             CognitiveFamily, SubproblemDiscovery)
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.canonical_state import CanonicalWorkState, ExecutionPlan, ExecutionStep
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.cognitive_engine import (SemanticProposal, StructuralProposal,
                                                 TestDoubleCognitiveEngine)
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.problem_compiler import (CANDIDATE_WITHOUT_OWNER, CANDIDATE_WITHOUT_SOURCE,
                                                 CAPABILITY_WITHOUT_COGNITIVE_OWNER,
                                                 DISCOVERY_PAYLOAD_MISUSE, DUPLICATE_CANDIDATE,
                                                 INVALID_PREDICATE, PREDICATE_UNGROUNDED,
                                                 REJECTION_CODES, SEGREGATION_WITHOUT_DISCOVERY,
                                                 SEGREGATION_WITHOUT_FAMILY, TASK_REF_NOT_IN_NETWORK,
                                                 UNAUTHORIZED_OWNER, UNGROUNDED_SOURCE,
                                                 UNKNOWN_CAPABILITY, UNKNOWN_DEPENDENCY_TARGET,
                                                 CandidateKind, CandidateRejection, ProblemCandidate,
                                                 ProblemCompilation, ProblemCompiler,
                                                 ProblemCompilerError, _Judge)
from src.eureka.universe.problem_model import (CognitiveTask, ProblemModel, StructuredProblem,
                                               TaskNetwork)
from src.eureka.universe.work_model import EurekaWork

FIXED_NOW = "2026-09-12T00:00:00+00:00"
_UNIVERSE_DIR = os.path.dirname(os.path.abspath(inspect.getfile(ProblemCompiler)))
_MODULE_PATH = os.path.join(_UNIVERSE_DIR, "problem_compiler.py")
_PRE_CHANGE = os.path.join("_scratch", "loop4", "PRE_CHANGE_FINGERPRINTS.json")


# -------------------------------------------------------------------------------------------- #
# helpers
# -------------------------------------------------------------------------------------------- #
def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _compiler() -> ProblemCompiler:
    return ProblemCompiler(_reg())


def _task(task_id: str, owner: str = "EM Descriptor", deps=None, outputs=None) -> CognitiveTask:
    return CognitiveTask(task_id=task_id, description=f"task {task_id}", owner=owner,
                         expected_outputs=outputs or [f"out-{task_id}"],
                         dependencies=list(deps or []))


def _sp(tasks=None, **kw) -> StructuredProblem:
    sp = StructuredProblem(
        questions=kw.get("questions", []), entities=kw.get("entities", []),
        variables=kw.get("variables", []), relationships=kw.get("relationships", []),
        assumptions=kw.get("assumptions", []), unknowns=kw.get("unknowns", []),
        evidence_requirements=kw.get("evidence_requirements", []),
        constraints=kw.get("constraints", []), success_criteria=kw.get("success_criteria", []),
    )
    sp.task_network = TaskNetwork(tasks=list(tasks or []))
    return sp


def _pm(**kw) -> ProblemModel:
    return ProblemModel(intent=kw.pop("intent", "intent"), objective=kw.pop("objective", "objective"),
                        problem_id=kw.pop("problem_id", "PROB-L4"), **kw)


def _compile(problem=None, structured=None, **kw):
    return _compiler().compile(problem or _pm(), structured or _sp(), now=FIXED_NOW, **kw)


def _cand(kind=CandidateKind.TASK, source="problem.risk", owner="EM Predictor", **kw) -> ProblemCandidate:
    data = dict(candidate_id="X", kind=kind, source=source, reason="r", cognitive_owner=owner)
    data.update(kw)
    return ProblemCandidate(**data)


def _gate(raw, problem=None, structured=None):
    judge = _Judge(problem or _pm(), structured or _sp(), [], None, (), _reg())
    return judge.gate(list(raw))


# ============================================================================================= #
# 0. AUTHORITY / NON-DUPLICATION (structural, by introspection — not by convention)
# ============================================================================================= #
def test_compiler_public_surface_has_no_agent_routing_or_persistence_api():
    public = [m for m in dir(ProblemCompiler) if not m.startswith("_")]
    methods = [m for m in public if callable(getattr(ProblemCompiler, m))]
    assert public == ["AUTHORITY", "TASK_NETWORK_AUTHORITY", "compile"]
    assert methods == ["compile"]                       # exactly ONE operation: enrich
    for marker in ("agent", "rout", "register", "authorize", "persist", "store", "create",
                   "write", "save", "task"):
        assert not any(marker in m.lower() for m in methods), marker


def test_compiler_is_stateless_across_compilations():
    compiler = _compiler()
    compiler.compile(_pm(unknowns=["a"]), _sp(), now=FIXED_NOW)
    compiler.compile(_pm(problem_id="PROB-OTHER", unknowns=["b"]), _sp(), now=FIXED_NOW)
    assert list(compiler.__dict__.keys()) == ["cap_registry"]      # no per-work state


def test_compiler_declares_enrichment_only_and_the_single_task_network_authority():
    assert ProblemCompiler.AUTHORITY == "ENRICHMENT_ONLY"
    assert ProblemCompiler.TASK_NETWORK_AUTHORITY == "EMStructurer"
    compilation = _compile()
    assert compilation.authority == "ENRICHMENT_ONLY"
    assert compilation.task_network_authority == "EMStructurer"
    assert compilation.enrichment_only is True


def test_compilation_is_not_a_second_task_network_or_a_routing_authority():
    fields = set(ProblemCompilation.model_fields)
    for forbidden in ("tasks", "task_network", "steps", "selected_ems", "next_owner", "routing"):
        assert forbidden not in fields, forbidden
    # a candidate may REFERENCE an existing task; it may not carry a task definition of its own
    assert "description" not in ProblemCandidate.model_fields
    assert "owner" not in ProblemCandidate.model_fields      # ownership is `cognitive_owner` (candidate field)
    assert ProblemCandidate.model_fields["task_ref"].default is None


def test_module_never_imports_the_agent_layer_foundation_or_the_sdk():
    """Structural scan of the CODE (not the prose): imports, names and calls are audited."""
    tree = ast.parse(open(_MODULE_PATH, encoding="utf-8").read())
    forbidden_imports = ("eureka.foundation", "eureka_cognitive_sdk", "requests", "os",
                         "agent_registry", "agent_runtime", "agent_definition")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(forbidden_imports), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(forbidden_imports), node.module
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for forbidden_name in ("WorkStore", "CanonicalWorkState", "AgentRegistry", "AgentRuntime",
                           "AgentFactory", "requests", "json"):
        assert forbidden_name not in used, forbidden_name
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            assert not (isinstance(func, ast.Name) and func.id == "open"), "no file I/O allowed"
            assert not (isinstance(func, ast.Attribute) and func.attr in ("dump", "write_text")), \
                "no persistence allowed"


def test_no_agent_is_created_or_authorised_by_compilation():
    compilation = _compile(_pm(unknowns=["u"]), _sp(tasks=[_task("t1")]))
    assert compilation.candidates
    assert all(not isinstance(c, AgentNetworkState) for c in compilation.candidates)
    # the compilation container itself has no agent field
    assert "agents" not in ProblemCompilation.model_fields
    assert not hasattr(ProblemCompiler, "AgentNetworkState".lower())


def test_ownership_is_always_one_of_the_constitutional_ems():
    compilation = _compile(_pm(required_capabilities=["analyze_dataset", "generate_summary"]),
                           _sp(tasks=[_task("t1"), _task("t2", owner="EM Predictor")]))
    owners = set(compilation.owners())
    assert owners and owners <= set(CONSTITUTIONAL_EM)
    assert all(c.cognitive_owner in CONSTITUTIONAL_EM for c in compilation.candidates)


# ============================================================================================= #
# 1-9. THE MANDATED ENRICHMENT FAMILIES
# ============================================================================================= #
def test_1_simple_problem_yields_traceable_candidates():
    compilation = _compile(_pm(), _sp(tasks=[_task("t1")]))
    kinds = {c.kind for c in compilation.candidates}
    assert CandidateKind.TASK in kinds
    for c in compilation.candidates:
        assert c.candidate_id.startswith("CAND-")
        assert c.source and c.reason                      # traceability is mandatory
        assert c.cognitive_owner in CONSTITUTIONAL_EM
        assert c.uncertainty in ("UNKNOWN", "LOW", "MEDIUM", "HIGH")
        assert c.coordination_cost == "NOT_ESTIMATED"      # never a fabricated number


def test_2_composite_problem_enriches_every_family_without_touching_the_network():
    sp = _sp(tasks=[_task("t1"), _task("t2"), _task("t3", owner="EM Predictor", deps=["t1"]),
                    _task("t4", owner="EM Predictor", deps=["t2"])],
             variables=["precio", "demanda"], entities=["Europa"],
             relationships=["precio -> demanda"], unknowns=["estacionalidad"],
             evidence_requirements=["logs"])
    problem = _pm(unknowns=["falta coste"], risk="riesgo de datos sesgados",
                  required_capabilities=["analyze_dataset", "evaluate_alternatives"])
    before = sp.model_dump(mode="json")
    compilation = _compile(problem, sp)
    assert compilation.counts() == {"PREDICATE": 1, "KNOWLEDGE_GAP": 3, "REQUIRED_CAPABILITY": 2,
                                    "TASK": 4, "SEGREGATION": 2, "DEPENDENCY": 2, "UNCERTAINTY": 1}
    assert sp.model_dump(mode="json") == before                 # TaskNetwork untouched
    assert compilation.task_network_snapshot == ["t1", "t2", "t3", "t4"]


def test_3_multiple_predicates_are_specs_grounded_in_declared_symbols():
    sp = _sp(variables=["precio", "demanda"], entities=["Europa"],
             relationships=["precio -> demanda", "estacionalidad -> demanda",
                            "competencia -> precio"])
    compilation = _compile(_pm(), sp)
    preds = compilation.by_kind(CandidateKind.PREDICATE)
    assert len(preds) == 3
    assert {p.reference for p in preds} == {"precio -> demanda", "estacionalidad -> demanda",
                                            "competencia -> precio"}
    for p in preds:
        assert p.cognitive_owner == FAMILY_OWNER[CognitiveFamily.PREDICTOR]
        assert p.expected_value == ""                          # nothing declared -> nothing invented
        assert not hasattr(p, "logical_structure")             # NOT a PredictivePredicate
        assert not hasattr(p, "mse")


def test_4_knowledge_gaps_reuse_the_declared_unknowns_vocabulary():
    problem = _pm(unknowns=["falta coste unitario"])
    sp = _sp(unknowns=["estacionalidad"], evidence_requirements=["logs de mantenimiento"])
    compilation = _compile(problem, sp)
    gaps = compilation.by_kind(CandidateKind.KNOWLEDGE_GAP)
    assert [g.reference for g in gaps] == ["falta coste unitario", "estacionalidad",
                                           "logs de mantenimiento"]
    assert [g.source for g in gaps] == ["problem.unknowns[0]", "structured_problem.unknowns[0]",
                                        "structured_problem.evidence_requirements[0]"]
    assert all(g.cognitive_owner == FAMILY_OWNER[CognitiveFamily.DESCRIPTOR] for g in gaps)
    assert all(g.evidence_refs == [] for g in gaps)             # no evidence claimed/defaulted


def test_5_required_capabilities_resolve_against_the_existing_registry():
    problem = _pm(required_capabilities=["analyze_dataset", "generate_summary",
                                         "generate_chart", "no_existe"])
    compilation = _compile(problem, _sp())
    caps = compilation.by_kind(CandidateKind.REQUIRED_CAPABILITY)
    assert {c.reference for c in caps} == {"analyze_dataset", "generate_summary"}
    assert {c.cognitive_owner for c in caps} == {"EM Predictor", "EM Publisher"}
    codes = {r.reason_code for r in compilation.rejections}
    assert UNKNOWN_CAPABILITY in codes                          # 'no_existe' never invented
    assert CAPABILITY_WITHOUT_COGNITIVE_OWNER in codes          # 'generate_chart' -> canonical_em None


def test_5b_capabilities_already_planned_by_core_are_read_not_rerouted():
    plan = ExecutionPlan(steps=[ExecutionStep(step_id="s1", capability_id="extract_relevant_information",
                                              target="EM[SEMANTIC]", canonical_em="EM Descriptor",
                                              status="PENDING", dependencies=[],
                                              expected_outputs=[], produces_result=False)])
    compilation = _compile(_pm(), _sp(), execution_plan=plan)
    caps = compilation.by_kind(CandidateKind.REQUIRED_CAPABILITY)
    assert [c.reference for c in caps] == ["extract_relevant_information"]
    assert caps[0].source == "execution_plan.steps[0].capability_id"
    assert caps[0].cognitive_owner == "EM Descriptor"
    assert plan.steps[0].canonical_em == "EM Descriptor"        # routing untouched by the compiler


def test_6_task_candidates_reference_the_existing_cognitive_tasks():
    sp = _sp(tasks=[_task("t1"), _task("t2", deps=["t1"])])
    compilation = _compile(_pm(), sp)
    tasks = compilation.by_kind(CandidateKind.TASK)
    assert [t.task_ref for t in tasks] == ["t1", "t2"]
    assert [t.expected_value for t in tasks] == ["out-t1", "out-t2"]
    network_ids = [t.task_id for t in sp.task_network.tasks]
    assert all(t.task_ref in network_ids for t in tasks)         # points at the ONE authority


def test_7_segregation_candidates_reuse_subproblem_discovery_and_need_real_independence():
    # two Descriptor tasks with NO edge between them -> segregable; the Predictor task depends on t1
    sp = _sp(tasks=[_task("t1"), _task("t2"), _task("t3", owner="EM Predictor", deps=["t1"])])
    compilation = _compile(_pm(), sp)
    segs = compilation.by_kind(CandidateKind.SEGREGATION)
    assert len(segs) == 1
    seg = segs[0]
    assert isinstance(seg.discovery, SubproblemDiscovery)
    assert seg.discovery.proposed_family == CognitiveFamily.DESCRIPTOR
    assert seg.cognitive_owner == FAMILY_OWNER[CognitiveFamily.DESCRIPTOR]
    assert set(seg.dependencies) == {"t1", "t2"}
    assert seg.discovery.reason and seg.discovery.statement
    assert seg.discovery.proposed_predicate == ""                # no invented predicate
    assert seg.coordination_cost == "NOT_ESTIMATED"


def test_7b_dependent_same_family_tasks_are_not_segregable():
    sp = _sp(tasks=[_task("t1"), _task("t2", deps=["t1"])])       # t2 depends on t1
    compilation = _compile(_pm(), sp)
    assert compilation.by_kind(CandidateKind.SEGREGATION) == []


def test_8_dependencies_are_read_from_the_network_and_out_of_network_edges_fail_closed():
    sp = _sp(tasks=[_task("t1"), _task("t2", deps=["t1"])])
    compilation = _compile(_pm(), sp)
    deps = compilation.by_kind(CandidateKind.DEPENDENCY)
    assert [d.reference for d in deps] == ["t2->t1"]
    assert deps[0].dependencies == ["t2", "t1"]
    assert deps[0].cognitive_owner == "EM Descriptor"

    # an edge to a task that does not exist in the TaskNetwork is rejected, not accepted
    accepted, rejections = _gate([_cand(kind=CandidateKind.DEPENDENCY, source="x", owner="EM Descriptor",
                                        reference="t9->t404")], structured=_sp())
    assert accepted == []
    assert rejections[0].reason_code == UNKNOWN_DEPENDENCY_TARGET


def test_9_uncertainty_comes_from_declared_risk_and_never_double_counts_unknowns():
    problem = _pm(risk="riesgo declarado no cuantificado", unknowns=["falta dato"])
    compilation = _compile(problem, _sp(unknowns=["otro unknown"]))
    unc = compilation.by_kind(CandidateKind.UNCERTAINTY)
    assert len(unc) == 1
    assert unc[0].source == "problem.risk"
    assert unc[0].uncertainty == "UNKNOWN"                       # never a fabricated confidence
    assert unc[0].cognitive_owner == FAMILY_OWNER[CognitiveFamily.PREDICTOR]
    refs = [c.reference for c in compilation.candidates if c.kind == CandidateKind.UNCERTAINTY]
    assert "falta dato" not in refs                              # unknowns stay KNOWLEDGE_GAP
    assert _compile(_pm(), _sp()).by_kind(CandidateKind.UNCERTAINTY) == []


# ============================================================================================= #
# 10-19. CONTRACT CASES
# ============================================================================================= #
def test_10_problem_without_candidates_compiles_honestly():
    compilation = _compile(_pm(), _sp())
    assert compilation.is_empty() is True
    assert compilation.counts() == {k.value: 0 for k in CandidateKind}
    assert compilation.rejections == []
    assert compilation.candidate_ids() == []
    assert compilation.task_network_snapshot == []


def test_11_duplicate_candidates_keep_the_first_and_record_the_rejection():
    problem = _pm(unknowns=["mismo gap", "mismo gap"])            # same reference, different sources
    compilation = _compile(problem, _sp())
    gaps = compilation.by_kind(CandidateKind.KNOWLEDGE_GAP)
    assert len(gaps) == 1
    assert [r.reason_code for r in compilation.rejections] == [DUPLICATE_CANDIDATE]
    assert compilation.rejections[0].source == "problem.unknowns[1]"

    # duplicate TASK candidates (same task_id twice in the network)
    sp = _sp(tasks=[_task("dup"), _task("dup")])
    dup = _compile(_pm(), sp)
    assert len(dup.by_kind(CandidateKind.TASK)) == 1
    assert [r.reason_code for r in dup.rejections] == [DUPLICATE_CANDIDATE]

    # duplicate SEGREGATION candidates (same family payload twice)
    disc = SubproblemDiscovery(statement="s", proposed_family=CognitiveFamily.DESCRIPTOR, reason="r")
    seg = _cand(kind=CandidateKind.SEGREGATION, source="structured_problem.task_network.tasks[].owner",
                owner="EM Descriptor", reference="DESCRIPTOR", discovery=disc)
    accepted, rejections = _gate([seg, seg], structured=_sp(tasks=[_task("t1"), _task("t2")]))
    assert len(accepted) == 1
    assert rejections[-1].reason_code == DUPLICATE_CANDIDATE


def test_12_invalid_and_ungrounded_predicates_are_rejected():
    sp = _sp(relationships=["   ", "variable-inventada -> target-inventado"],
             variables=["precio"], entities=["Europa"])
    compilation = _compile(_pm(), sp)
    assert compilation.by_kind(CandidateKind.PREDICATE) == []
    codes = [r.reason_code for r in compilation.rejections]
    assert codes == [INVALID_PREDICATE, PREDICATE_UNGROUNDED]
    assert all(r.kind == CandidateKind.PREDICATE for r in compilation.rejections)


def test_13_candidate_without_source_is_rejected():
    accepted, rejections = _gate([_cand(source="")])
    assert accepted == []
    assert rejections[0].reason_code == CANDIDATE_WITHOUT_SOURCE

    accepted, rejections = _gate([_cand(source="structured_problem.relationships[9]",
                                        kind=CandidateKind.PREDICATE)])
    assert accepted == []
    assert rejections[0].reason_code == UNGROUNDED_SOURCE


def test_14_candidate_without_ownership_is_rejected():
    accepted, rejections = _gate([_cand(owner="")])
    assert accepted == []
    assert rejections[0].reason_code == CANDIDATE_WITHOUT_OWNER

    accepted, rejections = _gate([_cand(owner="EM Rogue")])
    assert accepted == []
    assert rejections[0].reason_code == UNAUTHORIZED_OWNER


def test_15_absent_evidence_is_never_converted_into_evidence():
    problem = _pm(evidence_requirements=["EVI-9999", "necesitamos datos de coste"],
                  unknowns=["gap sin evidencia"])
    compilation = _compile(problem, _sp())                        # NO available evidence ids supplied
    assert compilation.available_evidence_ids == []
    assert all(c.evidence_refs == [] for c in compilation.candidates)

    # only an EXACT, really-available id is bound — a look-alike text never becomes evidence
    bound = _compile(problem, _sp(), available_evidence_ids=("EVI-9999",))
    by_ref = {c.reference: c.evidence_refs for c in bound.by_kind(CandidateKind.KNOWLEDGE_GAP)}
    assert by_ref["EVI-9999"] == ["EVI-9999"]
    assert by_ref["necesitamos datos de coste"] == []
    assert by_ref["gap sin evidencia"] == []


def test_16_backwards_compatibility_with_legacy_canonical_states():
    # (a) a legacy canonical state (no `problem_compilation` key) loads with None and unchanged identity
    canonical = CanonicalWorkState(
        work=EurekaWork(work_id="WORK-LEGACY", title="t", user_intent="u",
                        task_category="c", problem_statement="p"))
    canonical.problem = _pm()
    assert canonical.problem_compilation is None
    payload = canonical.model_dump(mode="json")
    payload.pop("problem_compilation")
    assert CanonicalWorkState.model_validate(payload).problem_compilation is None

    # (b) REAL persisted works still load and their canonical identity is UNCHANGED
    if not os.path.exists(_PRE_CHANGE):
        pytest.skip("pre-change fingerprint evidence artifact not present in this checkout")
    evidence = json.load(open(_PRE_CHANGE, encoding="utf-8"))
    from src.eureka.universe.work_store import WorkStore, CorruptWorkError
    store = WorkStore()
    compared = 0
    for work_id in store.list():
        expected = evidence["fingerprints"].get(work_id)
        if expected is None:
            continue                                              # unreadable before the change
        try:
            state = store[work_id]
        except CorruptWorkError:
            continue
        assert state.problem_compilation is None                   # legacy state: honest NOT_COMPILED
        assert canonical_state_fingerprint(state) == expected, work_id
        compared += 1
    assert compared > 0, "no readable persisted work to compare against"


def test_17_compilation_is_deterministic_and_reproducible():
    problem = _pm(unknowns=["g"], risk="r", required_capabilities=["analyze_dataset"])
    sp = _sp(tasks=[_task("t1"), _task("t2", owner="EM Predictor", deps=["t1"])],
             variables=["precio"], relationships=["precio -> demanda"], unknowns=["u"])
    first = _compile(problem, sp, work_id="WORK-1", available_evidence_ids=("EVI-1",))
    second = _compile(problem, sp, work_id="WORK-1", available_evidence_ids=("EVI-1",))
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.compilation_id == second.compilation_id
    assert first.candidate_ids() == second.candidate_ids()


def test_18_cross_work_isolation_fails_closed_and_leaks_nothing():
    compiler = _compiler()
    with pytest.raises(ProblemCompilerError) as err:
        compiler.compile(_pm(), _sp(tasks=[_task("t1")]), work_id="WORK-A",
                         expected_work_id="WORK-B", now=FIXED_NOW)
    assert err.value.reason_code == "CROSS_WORK_CONTAMINATION"

    a = compiler.compile(_pm(problem_id="PROB-A", unknowns=["solo A"]), _sp(), work_id="WORK-A",
                         now=FIXED_NOW)
    b = compiler.compile(_pm(problem_id="PROB-B", unknowns=["solo B"]), _sp(), work_id="WORK-B",
                         now=FIXED_NOW)
    assert [c.reference for c in a.candidates] == ["solo A"]
    assert [c.reference for c in b.candidates] == ["solo B"]
    assert a.work_id == "WORK-A" and b.work_id == "WORK-B"
    assert a.compilation_id != b.compilation_id


def test_19_cross_problem_isolation_fails_closed():
    with pytest.raises(ProblemCompilerError) as err:
        _compiler().compile(_pm(problem_id="PROB-A"), _sp(), work_id="WORK-A",
                            expected_problem_id="PROB-B", now=FIXED_NOW)
    assert err.value.reason_code == "CROSS_PROBLEM_CONTAMINATION"


# ============================================================================================= #
# ADVERSARIAL SET
# ============================================================================================= #
def test_adv_second_task_network_cannot_be_created():
    sp = _sp(tasks=[_task("t1")])
    compilation = _compile(_pm(unknowns=["u"]), sp)
    assert [t.task_id for t in sp.task_network.tasks] == ["t1"]      # the ONE network, untouched
    assert len(sp.task_network.tasks) == 1
    assert not hasattr(compilation, "tasks")


def test_adv_task_network_mutation_attempt_fails_closed(monkeypatch):
    def _mutating_task_candidates(self):
        self.structured.task_network.tasks.append(_task("injected"))
        return []

    monkeypatch.setattr(_Judge, "task_candidates", _mutating_task_candidates)
    with pytest.raises(ProblemCompilerError) as err:
        _compile(_pm(), _sp(tasks=[_task("t1")]))
    assert err.value.reason_code == "TASK_NETWORK_MUTATION_ATTEMPT"


def test_adv_canonical_state_is_never_mutated_by_compilation():
    problem = _pm(unknowns=["u"], risk="r", required_capabilities=["analyze_dataset"])
    sp = _sp(tasks=[_task("t1"), _task("t2")], variables=["v"], relationships=["v -> w"])
    problem_before, sp_before = problem.model_dump(mode="json"), sp.model_dump(mode="json")
    _compile(problem, sp)
    assert problem.model_dump(mode="json") == problem_before
    assert sp.model_dump(mode="json") == sp_before


def test_adv_ownership_spoofing_is_rejected():
    accepted, rejections = _gate([_cand(owner="Agent-X")])
    assert accepted == [] and rejections[0].reason_code == UNAUTHORIZED_OWNER

    # a segregation candidate whose family is owned by another EM is a spoof
    disc = SubproblemDiscovery(statement="s", proposed_family=CognitiveFamily.DESCRIPTOR, reason="r")
    seg = _cand(kind=CandidateKind.SEGREGATION, source="structured_problem.task_network.tasks[].owner",
                owner="EM Predictor", reference="DESCRIPTOR", discovery=disc)
    accepted, rejections = _gate([seg], structured=_sp(tasks=[_task("t1"), _task("t2")]))
    assert accepted == [] and rejections[0].reason_code == UNAUTHORIZED_OWNER


def test_adv_segregation_without_discovery_or_with_misused_payload_is_rejected():
    accepted, rejections = _gate([_cand(kind=CandidateKind.SEGREGATION, owner="EM Descriptor",
                                        source="structured_problem.task_network.tasks[].owner")])
    assert accepted == [] and rejections[0].reason_code == SEGREGATION_WITHOUT_DISCOVERY

    disc = SubproblemDiscovery(statement="s", proposed_family=CognitiveFamily.DESCRIPTOR, reason="r")
    accepted, rejections = _gate([_cand(kind=CandidateKind.TASK, owner="EM Descriptor",
                                        source="problem.risk", discovery=disc)])
    assert accepted == [] and rejections[0].reason_code == DISCOVERY_PAYLOAD_MISUSE

    # a segregation candidate whose discovery declares NO family is rejected (no orphan ownership)
    no_family = SubproblemDiscovery(statement="s", reason="r")          # proposed_family=None
    seg = _cand(kind=CandidateKind.SEGREGATION, owner="EM Descriptor",
                source="structured_problem.task_network.tasks[].owner", discovery=no_family)
    accepted, rejections = _gate([seg], structured=_sp(tasks=[_task("t1"), _task("t2")]))
    assert accepted == [] and rejections[0].reason_code == SEGREGATION_WITHOUT_FAMILY


def test_adv_task_ref_outside_the_network_is_rejected():
    accepted, rejections = _gate([_cand(kind=CandidateKind.TASK, source="problem.risk",
                                        owner="EM Descriptor", task_ref="t404")],
                                 structured=_sp(tasks=[_task("t1")]))
    assert accepted == [] and rejections[0].reason_code == TASK_REF_NOT_IN_NETWORK


def test_adv_authority_escalation_is_impossible_by_construction():
    # authority is a module constant, not a field a candidate could carry
    assert "authority" not in ProblemCandidate.model_fields
    assert "authority_scope" not in ProblemCandidate.model_fields
    assert ProblemCompilation.model_fields["authority"].default == "ENRICHMENT_ONLY"
    with pytest.raises(ProblemCompilerError) as err:
        ProblemCompilation(compilation_id="C", authority="AUTHORITY")
    assert err.value.reason_code == "COMPILER_AUTHORITY_CANNOT_BE_ESCALATED"
    with pytest.raises(ProblemCompilerError):
        ProblemCompilation(compilation_id="C", task_network_authority="ProblemCompiler")
    with pytest.raises(ProblemCompilerError):
        ProblemCompilation(compilation_id="C", enrichment_only=False)


def test_adv_no_second_compiler_authority_is_created():
    compilation = _compile(_pm(unknowns=["u"]), _sp(tasks=[_task("t1")]))
    # the compilation points AT the existing authorities instead of replicating them
    assert compilation.authority == "ENRICHMENT_ONLY"
    assert compilation.task_network_authority == "EMStructurer"
    assert not hasattr(compilation, "problem_model")             # no second ProblemModel
    assert "problem" not in ProblemCompilation.model_fields
    assert "structured_problem" not in ProblemCompilation.model_fields


def test_adv_rejection_codes_are_declared_and_used():
    assert len(set(REJECTION_CODES)) == len(REJECTION_CODES)
    for code in (CANDIDATE_WITHOUT_SOURCE, UNGROUNDED_SOURCE, CANDIDATE_WITHOUT_OWNER,
                 UNAUTHORIZED_OWNER, UNKNOWN_CAPABILITY, CAPABILITY_WITHOUT_COGNITIVE_OWNER,
                 INVALID_PREDICATE, PREDICATE_UNGROUNDED, SEGREGATION_WITHOUT_DISCOVERY,
                 DISCOVERY_PAYLOAD_MISUSE, DUPLICATE_CANDIDATE, UNKNOWN_DEPENDENCY_TARGET):
        assert code in REJECTION_CODES
    assert CandidateRejection(reason_code=CANDIDATE_WITHOUT_SOURCE).kind is None


# ============================================================================================= #
# LOCAL E2E through the REAL orchestrator (ProblemModel -> Core -> Structurer -> Orchestrator ->
# TaskNetwork -> ProblemCompiler enrichment). Deterministic provider double: no model call.
# ============================================================================================= #
E2E_INTENT = "LOOP4 E2E: evaluar el impacto del precio en la demanda en Europa y decidir el plan"


def _e2e_orchestrator() -> WorkOrchestrator:
    engine = TestDoubleCognitiveEngine()
    engine.semantic_fixtures[E2E_INTENT] = SemanticProposal(
        intent_category="DECISION",
        problem_understanding="Impacto del precio sobre la demanda",
        objective="Evaluar el impacto del precio en la demanda y decidir el plan",
        context="Europa", evidence_requirements=["serie historica de precios", "EVI-L4-1"],
        constraints=["sin datos personales"], unknowns=["elasticidad real"],
        risk="sesgo de seleccion", questions=["¿es estable la elasticidad?"],
        assumptions=["mercado competitivo"],
    )
    engine.structural_fixtures[E2E_INTENT] = StructuralProposal(
        entities=["Europa"], variables=["precio", "demanda"],
        relationships=["precio -> demanda"],
        unknowns=["elasticidad real"], evidence_requirements=["serie historica de precios"],
        task_proposals=[
            CognitiveTask(task_id="E2E-T1", description="Establish current state",
                          owner="EM Descriptor", expected_outputs=["current state"], dependencies=[]),
            CognitiveTask(task_id="E2E-T2", description="Identify explanatory factors",
                          owner="EM Descriptor", expected_outputs=["factors"], dependencies=[]),
            CognitiveTask(task_id="E2E-T3", description="Predict scenario",
                          owner="EM Predictor", expected_outputs=["prediction"],
                          dependencies=["E2E-T1", "E2E-T2"]),
        ],
    )
    return WorkOrchestrator(_reg(), engine)


def test_e2e_local_compilation_enrichment_through_the_real_orchestrator():
    canonical = _e2e_orchestrator().orchestrate(E2E_INTENT)

    # 1. the TaskNetwork keeps ONE authority: the Structurer's network (+ the Publisher task Core
    #    itself injects downstream), read by the compiler and NEVER modified by it
    network = canonical.problem.structured_problem.task_network
    network_ids = [t.task_id for t in network.tasks]
    assert network_ids[:3] == ["E2E-T1", "E2E-T2", "E2E-T3"]        # the Structurer's tasks, in order
    assert network_ids[3:] == ["task_publish"]                     # injected by EM Core, not by us
    assert canonical.problem_compilation is not None
    assert canonical.problem_compilation.task_network_snapshot == network_ids
    assert canonical.problem_compilation.task_network_authority == "EMStructurer"

    # 2. ProblemCompiler only ENRICHES: candidates exist, the network has no candidate tasks
    compilation = canonical.problem_compilation
    assert compilation.candidates
    assert not any(t.task_id.startswith("CAND-") for t in network.tasks)

    # 3. candidates are traceable (source + reason + owner + deterministic id)
    for c in compilation.candidates:
        assert c.candidate_id.startswith("CAND-") and c.source and c.reason
        assert c.cognitive_owner in CONSTITUTIONAL_EM

    # 4. no agent is created (agent layer untouched by LOOP 4)
    assert canonical.agent_network.records == []
    assert canonical.agent_network.executions == []

    # 5. no parallel routing: the plan's EM assignment is Core's, the compilation has no routing field
    assert not hasattr(compilation, "selected_ems")
    assert set(canonical.problem_compilation.owners()) <= set(CONSTITUTIONAL_EM)

    # 6. no new persistence authority: the compilation round-trips inside the canonical container
    reloaded = CanonicalWorkState.model_validate(canonical.model_dump(mode="json"))
    assert reloaded.problem_compilation.model_dump(mode="json") == compilation.model_dump(mode="json")

    # 7. canonical state stays governed: identity is the existing content identity (Q2)
    assert canonical_state_fingerprint(reloaded) == canonical_state_fingerprint(canonical)

    # 8. reproducible enrichment, work-scoped identity: two runs of the same problem produce the
    #    same candidates, while each NEW work gets its own compilation identity (cross-work isolation)
    again = _e2e_orchestrator().orchestrate(E2E_INTENT)
    a, b = canonical.problem_compilation, again.problem_compilation
    assert a.candidate_ids() == b.candidate_ids()
    assert a.counts() == b.counts()
    assert [c.kind for c in a.candidates] == [c.kind for c in b.candidates]
    assert [c.source for c in a.candidates] == [c.source for c in b.candidates]
    assert a.work_id == canonical.work.work_id and b.work_id == again.work.work_id
    assert a.work_id != b.work_id and a.compilation_id != b.compilation_id

    # the compilation is a planning artifact: it does NOT enter the Q2 content identity
    stripped = canonical.model_dump(mode="json")
    stripped.pop("problem_compilation")
    assert canonical_state_fingerprint(CanonicalWorkState.model_validate(stripped)) \
        == canonical_state_fingerprint(canonical)
