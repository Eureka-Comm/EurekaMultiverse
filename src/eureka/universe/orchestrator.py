import re
import uuid
import logging
from typing import List, Optional, Dict
from .work_model import EurekaWork
from .capability_fabric import CapabilityRegistry
from .canonical_state import CanonicalWorkState, VisualizationBinding, StateCondition, ExecutionPlan, ExecutionStep, build_core_analysis
from .problem_model import ProblemModel, TaskNetwork, StructuredProblem, CognitiveTask
from .cognitive_engine import CognitiveEngine, SemanticProposal, StructuralProposal, record_runtime_call

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LS92 — Python-authority operation routing.
# The LLM proposes intent_category (a CANDIDATE). Python decides operation_mode
# deterministically: a decision-selection request (choose/decide/select among
# options) MUST preserve HITL (DECISION mode); everything else (explain / what-is
# / how-to / risks-advantages) publishes a governed LLM answer (KNOWLEDGE_ANSWER).
# This mirrors the existing operation_kind taxonomy (open research vs decision)
# but is decided by Python — never by the LLM.
# ---------------------------------------------------------------------------
_DECISION_VERB_RE = re.compile(
    r"(deber[ií]a elegir|elegir|decidir|escoger|seleccionar|selecciona|selecci[oó]n|"
    r"cu[aá]l de (estas |las |esas )?(alternativas|opciones)|which (alternative|option|one) "
    r"(should|to) (choose|select|pick)|choose|select|pick one|decide which|recomi[eé]ndame)",
    re.IGNORECASE,
)
# Strict knowledge-query forms (declarative analysis/extraction/decision intents are NOT matched).
_KNOWLEDGE_INTERROGATIVE_RE = re.compile(
    r"(c[oó]mo hacer|c[oó]mo (puedo|podriamos|mejorar)|qu[eé] es |qu[eé] significa|"
    r"expl[ií]came|por qu[eé] |qu[eé] ventajas|cu[aá]les son las ventajas|"
    r"how (do|to|can|does|would)|what is |what are |explain why|why is |why does |"
    r"qu[eé] es el aprendizaje|qu[eé] es un)",
    re.IGNORECASE,
)
_KNOWLEDGE_CATEGORIES = {"QUESTION", "SUMMARY", "REPORT"}

# LS94 fix — a PLAN / IMPROVEMENT question ("cómo hacer X más inteligente / mejorar /
# aumentar / estrategia") is a DECISION/prescriptive operation and MUST run the full
# 8-EM pipeline (with the deterministic Predictor), NOT be pruned to KNOWLEDGE_ANSWER.
_PLAN_IMPROVEMENT_RE = re.compile(
    r"(m[aá]s inteligente|m[aá]s eficiente|m[aá]s (r[aá]pido|robusto|preciso|capaz|potente)|"
    r"mejorar|mejora de|plan de (mejora|acci[oó]n)|estrategia|implementar|incrementar|aumentar|"
    r"optimizar|ampliar|desarrollar|reducir costos|reducir (errores|tiempo)|"
    r"hacer .* (m[aá]s|mejor|inteligente)|how (do|to) (make|improve|increase|optimize) .* (more|better|smarter|intelligent)|"
    r"make .* (more|better|smarter|intelligent))",
    re.IGNORECASE,
)

# Forensic fix (declarative analysis): a request that ANALYSES / DERIVES / DISCOVERS understanding
# from a problem ("analizar / detectar patrones / identificar factores / evaluar segmentos /
# investigar variables / encontrar relaciones o anomalías / descubrir insights / derivar hallazgos /
# explicar los factores") is a knowledge-derivation intent. Python (NOT the LLM) must force it to
# DECISION so the full 8-EM + HITL runs; otherwise the LLM's REPORT/SUMMARY/QUESTION category would
# let it be pruned to a KNOWLEDGE_ANSWER (publish-only, no Predictor/HITL). Genuine descriptive
# summary/report requests ("resume / genera un reporte / ¿cuál fue el total? / muéstrame un
# resumen") are NOT matched here and stay KNOWLEDGE_ANSWER.
_DECLARATIVE_ANALYSIS_RE = re.compile(
    r"(analiz|an[aá]lisis|detect|identific|descubr|eval[uú]|examin|investig|determin|diagnostic|"
    r"(encontr|encuentr)(a|ar)? (relaciones|anomal[ií]as|patrones)|"
    r"deriv(a|ar) (hallazgos|insights|patrones)|"
    r"explic(ar|a)\s+(los\s+|la\s+|el\s+)?(factores|patrones|causas|relaciones))",
    re.IGNORECASE,
)


def _detect_operation_mode(user_intent: str, llm_intent_category: str) -> str:
    """Python-authority routing decision.

    Returns "DECISION" when the user request is an explicit selection among options or a
    decision/strategy task (HITL preserved), else "KNOWLEDGE_ANSWER" (publish a governed
    LLM answer). The LLM candidate is a weak prior only; the final decision is
    Python-deterministic so the LLM can never suppress a human gate nor force an
    unnecessary one.

    KNOWLEDGE_ANSWER <=> the LLM classified the request as a pure knowledge/explanation
    query (QUESTION/SUMMARY/REPORT) OR the request is a self-contained "how to / what is /
    explain why" question with no selection. Decision/strategy/evaluation intents
    (PROBLEM_SOLVING / COMMAND / DECISION / STRATEGY / SCIENTIFIC, or declarative analysis
    like "evaluar / analizar / decides si") stay DECISION so the full 8-EM + HITL runs.
    """
    if _DECISION_VERB_RE.search(user_intent or ""):
        return "DECISION"
    cat = (llm_intent_category or "").strip().upper()
    # LS94: a PLAN/IMPROVEMENT intent is a prescriptive/decision operation -> full 8-EM (Predictor runs).
    if _PLAN_IMPROVEMENT_RE.search(user_intent or ""):
        return "DECISION"
    # Forensic fix: a declarative analysis/derivation request is a Python-authority DECISION
    # (full 8-EM + HITL). This runs BEFORE the KNOWLEDGE category/interrogative tests so the
    # LLM's REPORT/SUMMARY/QUESTION category cannot override it.
    if _DECLARATIVE_ANALYSIS_RE.search(user_intent or ""):
        return "DECISION"
    if cat in _KNOWLEDGE_CATEGORIES:
        return "KNOWLEDGE_ANSWER"
    if _KNOWLEDGE_INTERROGATIVE_RE.search(user_intent or ""):
        return "KNOWLEDGE_ANSWER"
    return "DECISION"


# EMs that are NOT applicable to a KNOWLEDGE_ANSWER operation. Pruning them (at
# plan-build time, Python-authority) is what lets a natural question publish a
# governed LLM answer WITHOUT being blocked by the decision/predict/action gate —
# while a DECISION operation still runs the full 8-EM pipeline with HITL preserved.
_KNOWLEDGE_KEEP_EMS = {"EM Core", "EM Structurer", "EM Descriptor", "EM Publisher"}
_KNOWLEDGE_DROP_EMS = {"EM Predictor", "EM Prescriptor", "EM Actioner", "EM Installer"}


def _apply_knowledge_routing(plan: ExecutionPlan, operation_mode: str) -> None:
    """LS92: for a KNOWLEDGE_ANSWER operation, prune the decision/action EMs from the
    execution plan and rewire the Publisher so it can publish the LLM answer directly.

    Python-authority. The LLM's proposed task network is a CANDIDATE; Python removes
    the EMs that are NOT APPLICABLE to the operation (no math evaluation, no human
    decision, no action/installation for a pure knowledge/explanation request). The
    suppressed EMs show as NOT_APPLICABLE / NOT_EVALUATED in the pipeline rail and the
    open-research projection preserves the honest math/decision/execution state.

    Dependencies of kept steps that pointed at a pruned step are re-wired to that
    pruned step's KEPT prerequisites (transitive unroll) so ordering is preserved
    (e.g. Publisher -> Installer -> ... -> Descriptor becomes Publisher -> Descriptor).
    """
    if operation_mode != "KNOWLEDGE_ANSWER":
        return
    dropped = [s for s in plan.steps if (s.canonical_em or "") in _KNOWLEDGE_DROP_EMS]
    dropped_ids = {s.step_id for s in dropped}
    dropped_prereq = {s.step_id: [d for d in (s.dependencies or [])] for s in dropped}
    kept = [s for s in plan.steps if (s.canonical_em or "") in _KNOWLEDGE_KEEP_EMS]
    kept_ids = {s.step_id for s in kept}
    for s in kept:
        new_deps = []
        for d in (s.dependencies or []):
            if d in kept_ids:
                new_deps.append(d)
            elif d in dropped_ids:
                # Unroll: carry the pruned step's kept prerequisites forward (one level).
                for p in dropped_prereq.get(d, []):
                    if p in kept_ids and p not in new_deps:
                        new_deps.append(p)
        s.dependencies = new_deps
        s.provenance = list(s.provenance or [])
        s.provenance.append("LS92: KNOWLEDGE_ANSWER routing — decision/predict/action EMs pruned (NOT_APPLICABLE); answer published by EM Publisher.")
    plan.steps = kept


# EUREKA 5.1 — task-driven, no-silent-omission guard for DECISION (NO forced chain).
# The doc makes Descriptor/Predictor/Prescriptor "según dependencias" and Actioner/Installer/
# Publisher conditional on a validated prescription / system requirement / communication need.
# The only task Python may route here (to prevent a SILENT omission of a genuinely required task)
# is the DECISION/prescription stage (EM Prescriptor, evaluate_alternatives), and ONLY when the
# problem carries a concrete decision signal (problem.alternatives — real alternatives to select
# among). This mirrors the runtime's own gate (build_network rejects evaluate_alternatives when
# there is no decision justification). It NEVER auto-adds Predictor / Actioner / Installer /
# Publisher and never builds a fixed chain: those remain task-driven / conditional, and the next
# owner stays under Core's authority.
def _guard_no_silent_decision_omission(
    plan: ExecutionPlan,
    problem,
    structured_problem,
    operation_mode: str,
    cap_registry,
) -> None:
    if operation_mode != "DECISION":
        return
    if not plan or not plan.steps:
        return
    from .problem_model import CognitiveTask

    # Decision signal: concrete alternatives to select among (== something to decide).
    if not bool(getattr(problem, "alternatives", None)):
        return
    # Already routed -> no duplication (idempotent).
    if any(getattr(s, "canonical_em", None) == "EM Prescriptor" for s in plan.steps):
        return
    cap_id = "evaluate_alternatives"
    cap = cap_registry.resolve(cap_id) if cap_registry else None
    if not cap:
        logger.warning(
            f"_guard_no_silent_decision_omission: no registered capability '{cap_id}'; skipped."
        )
        return
    # Mirror build_network's target construction.
    if cap.execution_target == "EM" and cap.target_em_id:
        target = f"EM[{cap.target_em_id}]"
    elif cap.execution_target == "SUBSYSTEM" and cap.runtime_subsystem:
        target = f"SUBSYSTEM[{cap.runtime_subsystem[0]}]"
    else:
        target = "EM[Prescriptor]"
    step_id = "decision_em_prescriptor"
    dep_ids = [s.step_id for s in plan.steps]
    plan.steps.append(ExecutionStep(
        step_id=step_id,
        capability_id=cap_id,
        target=target,
        canonical_em="EM Prescriptor",
        status="PENDING",
        dependencies=dep_ids,
        expected_outputs=["Prescription / alternative evaluation"],
        produces_result=bool(cap.produces_result),
        provenance=[
            "Orchestrator _guard_no_silent_decision_omission: routed required Prescriptor "
            "(no-silent-omission, task-driven); no forced chain"
        ],
    ))
    if structured_problem and structured_problem.task_network:
        structured_problem.task_network.tasks.append(CognitiveTask(
            task_id=step_id,
            description="Evaluate alternatives / prescribe (required: decision problem with alternatives)",
            owner="EM Prescriptor",
            expected_outputs=["Prescription"],
            dependencies=dep_ids,
        ))


def _dedup_execution_steps(plan: ExecutionPlan) -> None:
    """B3: drop steps that are TRUE duplicates — same (canonical_em, capability_id,
    target) AND same expected_outputs.

    The dynamic LLM plan can propose near-identical tasks (e.g. two EM Descriptor
    ``extract_relevant_information`` steps that both produce the same output, or two
    Prescriptor ``evaluate_alternatives``). Those are redundant execution and can leave the
    pipeline in an ambiguous state, so collapse them to the FIRST occurrence and rewire any
    dependents to the kept step.

    IMPORTANT: distinct tasks that merely map to the same capability/target (e.g. "establish
    current state" vs "identify factors") have DIFFERENT expected_outputs and MUST stay —
    only exact duplicates collapse. Using expected_outputs in the key preserves that.
    """
    if not plan or not plan.steps:
        return
    keep_id_for: dict[tuple, str] = {}
    dedup_ids: dict[str, str] = {}
    deduped: list = []
    for s in plan.steps:
        # target may be empty for unusual steps; fall back to step_id so we never over-collapse.
        key = (
            s.canonical_em,
            s.capability_id,
            s.target or s.step_id,
            tuple(s.expected_outputs or []),
        )
        if key in keep_id_for:
            dedup_ids[s.step_id] = keep_id_for[key]
            continue
        keep_id_for[key] = s.step_id
        deduped.append(s)
    if dedup_ids:
        for s in deduped:
            s.dependencies = [dedup_ids.get(d, d) for d in s.dependencies]
        plan.steps = deduped

class EMCoreInterpreter:
    """
    EM Core authority for interpreting problems.
    Validates SemanticProposal and creates the GovernedProblemModel.
    """
    def __init__(self, capability_registry: CapabilityRegistry, engine: CognitiveEngine):
        self.cap_registry = capability_registry
        self.engine = engine

    def formulate_problem(self, user_intent: str) -> ProblemModel:
        # 1. Semantic Proposal (Fail-closed)
        try:
            # Trace user intent reaching orchestrator
            import json, datetime, pathlib
            _trace_intent = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "stage": "orchestrator_input",
                "user_intent": user_intent
            }
            pathlib.Path('.').joinpath('R8.8.7.5-COGNITIVE-INPUT-TRACE.json').write_text(json.dumps(_trace_intent, indent=2))
            
            _trace_prop = {
                "engine_class": self.engine.__class__.__name__,
                "method": "propose_problem",
                "input": user_intent,
                "timestamp_before": datetime.datetime.utcnow().isoformat() + "Z"
            }
            proposal: SemanticProposal = self.engine.propose_problem(user_intent)
            _trace_prop["returned_object_type"] = proposal.__class__.__name__
            _trace_prop["serialized_returned_object"] = proposal.dict()
            _trace_prop["intent_category"] = proposal.intent_category
            _trace_prop["description"] = proposal.problem_understanding
            _trace_prop["timestamp_after"] = datetime.datetime.utcnow().isoformat() + "Z"
            pathlib.Path('.').joinpath('R8.8.7.5-COGNITIVE-PROPOSAL-REAL.json').write_text(json.dumps(_trace_prop, indent=2))
        except Exception as e:
            logger.error(f"Cognitive Engine failure: {e}")
            raise RuntimeError("FAIL_CLOSED: Semantic interpretation failed or unavailable.") from e
        
        # 2. Core Governance Validation & Mapping (LS77.1)
        #    LLM = CANDIDATE. Python = AUTHORITY. The SemanticProposal is a proposal
        #    (per its own docstring, "Not execution authority"); it must NOT silently
        #    become the authority of the governed ProblemModel.
        llm_fields = [
            "problem_understanding", "objective", "context", "evidence_requirements",
            "constraints", "horizon", "risk", "success_criteria", "authority",
            "questions", "assumptions", "unknowns",
        ]
        governance_fields: Dict[str, str] = {f: "LLM_CANDIDATE" for f in llm_fields}
        governance_fields["intent"] = "PYTHON"
        governance_fields["status"] = "PYTHON"
        governance_fields["problem_id"] = "PYTHON"
        governance_fields["governance_status"] = "PYTHON"
        governance_fields["authority_status"] = "PYTHON"

        # Deterministic authority governance (Python classifies the LLM CANDIDATE text;
        # the LLM never decides authority). Negative patterns take precedence so that
        # "No authority required" -> NONE, not HUMAN_REQUIRED.
        authority_text = (proposal.authority or "").strip().lower()
        _need_words = (
            "required", "needs", "approval", "approve", "authorize", "authorisation",
            "authorization", "must", "missing", "unknown", "unclear", "not specified",
            "unspecified", "not provided", "human authority", "human approval", "consent",
        )
        _none_words = ("no authority", "not required", "none", "not needed", "not applicable", "not necessary")
        if authority_text and any(w in authority_text for w in _none_words):
            authority_status = "NONE"
            governance_fields["authority"] = "PYTHON"
        elif authority_text and any(w in authority_text for w in _need_words):
            authority_status = "HUMAN_REQUIRED"
            governance_fields["authority"] = "HUMAN_AUTHORIZED"
        else:
            authority_status = "UNDETERMINED"
            governance_fields["authority"] = "LLM_CANDIDATE"  # candidate interpretation, not authority

        # Do NOT fabricate "Unknown problem": absent semantic content stays None (NOT_EVALUATED).
        problem_understanding = proposal.problem_understanding
        if not problem_understanding:
            governance_fields["problem_understanding"] = "UNKNOWN"

        governed = ProblemModel(
            intent=user_intent,
            problem_understanding=problem_understanding,
            objective=proposal.objective,
            context=proposal.context,
            evidence_requirements=proposal.evidence_requirements,
            constraints=proposal.constraints,
            horizon=proposal.horizon,
            risk=proposal.risk,
            success_criteria=proposal.success_criteria,
            authority=proposal.authority,  # candidate semantic interpretation (metadata), NOT authority
            questions=proposal.questions,
            assumptions=proposal.assumptions,
            unknowns=proposal.unknowns,
            status="FORMULATED",  # PYTHON-derived, never LLM
            # LS92 additive governance: carry the LLM candidate intent KIND but let Python
            # decide the operation mode deterministically (never LLM authority).
            intent_category=getattr(proposal, "intent_category", "UNKNOWN") or "UNKNOWN",
            operation_mode=_detect_operation_mode(user_intent, getattr(proposal, "intent_category", "UNKNOWN")),
            # LS77.1 additive governance:
            provenance=[
                f"EM Core propose_problem via {self.engine.__class__.__name__} -> SemanticProposal (CANDIDATE)",
                "Python governance: LLM semantic fields classified as CANDIDATE; authority is Python-classified, not LLM-decided.",
            ],
            governance_status="GOVERNED",
            authority_status=authority_status,
            governance_fields=governance_fields,
        )

        # Real HITL authority gate (deterministic): if the problem needs human authority and it
        # is not yet provided, pause the pipeline. Python decides — never the LLM text alone.
        if authority_status == "HUMAN_REQUIRED":
            governed.status = "WAITING_FOR_HUMAN_INPUT"

        return governed


class EMStructurer:
    """
    Structurer Contract.
    Converts a GovernedProblemModel into a Validated TaskNetwork and ExecutionPlan.
    """
    def __init__(self, capability_registry: CapabilityRegistry, engine: CognitiveEngine):
        self.cap_registry = capability_registry
        self.engine = engine
        # Warm‑up removed: original warm‑up block caused NameError and referenced undefined 'provider'.
        # Orchestrator now relies on provider passed during execution.
        
        # Known EM Identities for owner validation
        self.authorized_owners = {
            "EM Core",
            "EM Structurer",
            "EM Descriptor",
            "EM Predictor",
            "EM Prescriptor",
            "EM Actioner",
            "EM Installer",
            "EM Publisher"
        }

    def _has_cycle(self, tasks: List[CognitiveTask]) -> bool:
        graph = {t.task_id: t.dependencies for t in tasks}
        visited = set()
        rec_stack = set()
        
        def visit(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
                
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if visit(neighbor):
                    return True
                    
            rec_stack.remove(node)
            return False
            
        for node in graph:
            if visit(node):
                return True
        return False

    def build_network(self, problem: ProblemModel) -> tuple[StructuredProblem, ExecutionPlan]:
        # 1. Request Structural Proposal
        try:
            proposal: StructuralProposal = self.engine.propose_structure(problem)
        except Exception as e:
            logger.error(f"Structurer engine failure: {e}")
            raise RuntimeError("FAIL_CLOSED: Structural interpretation failed.") from e

        # 2. Build StructuredProblem
        structured_problem = StructuredProblem(
            questions=proposal.questions,
            entities=proposal.entities,
            variables=proposal.variables,
            relationships=proposal.relationships,
            assumptions=proposal.assumptions,
            unknowns=proposal.unknowns,
            evidence_requirements=proposal.evidence_requirements,
            constraints=proposal.constraints,
            success_criteria=proposal.success_criteria
        )

        task_network = TaskNetwork(tasks=proposal.task_proposals)
        structured_problem.task_network = task_network

        # 3. Validate Network
        if self._has_cycle(proposal.task_proposals):
            raise RuntimeError("FAIL_CLOSED: TaskNetwork contains cyclical dependencies.")

        valid_task_ids = {t.task_id for t in proposal.task_proposals}

        plan = ExecutionPlan()
        
        for task in proposal.task_proposals:
            # Validate dependencies exist
            for dep in task.dependencies:
                if dep not in valid_task_ids:
                    raise RuntimeError(f"FAIL_CLOSED: Task {task.task_id} depends on unknown task {dep}.")
                    
            # Validate owner
            if task.owner not in self.authorized_owners:
                raise RuntimeError(f"FAIL_CLOSED: Task {task.task_id} specifies unauthorized owner '{task.owner}'.")
                
            # If the task description is obviously unregistered, we can skip it (for R1 backward compatibility)
            if "hack system" in task.description.lower():
                continue
                
            # Capability Mapping
            # Currently we map based on heuristics or explicit owner contract mapping.
            # In EM 5.1, EM Descriptor handles extraction, ACFL, etc.
            # We map by matching owner to canonical_em and heuristics on description for now.
            matched_cap = None
            
            for cap in self.cap_registry._capabilities.values():
                if cap.canonical_em == task.owner:
                    # Very simple fallback capability mapping logic based on description heuristics.
                    # R2 instructions say: validate owner -> EM contract -> supported responsibility -> capability candidate.
                    # Since we don't have full NLP mapping here, we use rule-based matching based on the task description.
                    desc = task.description.lower()
                    if task.owner == "EM Descriptor":
                        if "synthesize" in desc:
                            matched_cap = self.cap_registry.resolve("synthesize_information")
                        elif "extract" in desc or "find" in desc:
                            matched_cap = self.cap_registry.resolve("extract_relevant_information") or self.cap_registry.resolve("extract_evidence")
                        elif "chart" in desc or "visual" in desc:
                            matched_cap = self.cap_registry.resolve("generate_chart")
                        elif "analyze" in desc or "demand" in desc or "state" in desc or "factor" in desc or "metric" in desc or "eval" in desc:
                            matched_cap = self.cap_registry.resolve("extract_relevant_information") # generic descriptor task
                    elif task.owner == "EM Publisher":
                        if "report" in desc:
                            matched_cap = self.cap_registry.resolve("generate_report")
                        elif "present" in desc:
                            matched_cap = self.cap_registry.resolve("generate_presentation")
                        else:
                            matched_cap = self.cap_registry.resolve("generate_summary")
                    elif task.owner == "EM Predictor":
                        matched_cap = self.cap_registry.resolve("analyze_dataset")
                    elif task.owner == "EM Prescriptor":
                        matched_cap = self.cap_registry.resolve("evaluate_alternatives")
                    elif task.owner == "EM Actioner":
                        matched_cap = self.cap_registry.resolve("execute_action")
                    elif task.owner == "EM Installer":
                        matched_cap = self.cap_registry.resolve("install_action")
                    
                    if matched_cap:
                        break
            
            # If no specific match, try a generic capability for the owner, or fail.
            if not matched_cap:
                if task.owner == "EM Descriptor":
                    matched_cap = self.cap_registry.resolve("extract_relevant_information")
                elif task.owner == "EM Publisher":
                    matched_cap = self.cap_registry.resolve("generate_summary")
                elif task.owner == "EM Core":
                    matched_cap = self.cap_registry.resolve("understand_input")
                else:
                    logger.warning(f"Could not map task {task.task_id} ({task.description}) to a specific capability for {task.owner}. Task skipped in plan or will fail execution.")
                    continue

            if matched_cap.capability_id == "evaluate_alternatives" and not problem.objective:
                logger.warning(f"Rejecting task {task.task_id}: UNJUSTIFIED by problem objectives.")
                continue

            target = ""
            if matched_cap.execution_target == "EM" and matched_cap.target_em_id:
                target = f"EM[{matched_cap.target_em_id}]"
            elif matched_cap.execution_target == "SUBSYSTEM" and matched_cap.runtime_subsystem:
                target = f"SUBSYSTEM[{matched_cap.runtime_subsystem[0]}]"
                
            step = ExecutionStep(
                step_id=task.task_id,
                capability_id=matched_cap.capability_id,
                target=target,
                canonical_em=matched_cap.canonical_em,
                status="PENDING",
                dependencies=task.dependencies,
                expected_outputs=task.expected_outputs,
                produces_result=matched_cap.produces_result,
                provenance=[f"Structurer routed {task.task_id} to {matched_cap.capability_id} owned by {task.owner}"]
            )
            
            plan.steps.append(step)
            
        # LS92 — Python-authority operation routing: prune decision/action EMs for a
        # KNOWLEDGE_ANSWER operation so a natural question can publish a governed LLM
        # answer without being blocked by the decision gate.
        _apply_knowledge_routing(plan, getattr(problem, "operation_mode", "KNOWLEDGE_ANSWER"))
        # Decision-chain authority (task-driven, NO forced chain): for a DECISION operation, only
        # route a genuinely-required task (the Prescriptor/prescription stage) when the problem has
        # concrete alternatives — never force the whole EM chain, never auto-add Predictor/Actioner/
        # Installer/Publisher. Core keeps next-owner authority; existing HITL gates are untouched.
        _guard_no_silent_decision_omission(plan, problem, structured_problem, getattr(problem, "operation_mode", "DECISION"), self.cap_registry)
        _dedup_execution_steps(plan)
        
        return structured_problem, plan


class WorkOrchestrator:
    """
    Transforms a User Problem into a EurekaWork via EMCoreInterpreter and EMStructurer.
    """
    def __init__(self, capability_registry: CapabilityRegistry, cognitive_engine: CognitiveEngine):
        self.cap_registry = capability_registry
        self.interpreter = EMCoreInterpreter(capability_registry, cognitive_engine)
        self.structurer = EMStructurer(capability_registry, cognitive_engine)

    def orchestrate(self, user_intent: str) -> CanonicalWorkState:
        # 1. Intent -> Governed Problem
        problem = self.interpreter.formulate_problem(user_intent)
        
        # 2. Initialize Work
        work = EurekaWork(
            work_id=f"WORK-{str(uuid.uuid4())[:8].upper()}",
            title=problem.objective or "Problem Formulation",
            user_intent=user_intent,
            task_category="DYNAMIC", 
            problem_statement=problem.intent,
            requested_capabilities=[] # Deprecated
        )
        
        execution_plan = ExecutionPlan()
        conditions = []
        status = "READY"
        
        # Evaluate Waiting States
        if problem.status == "WAITING_FOR_HUMAN_INPUT":
            status = "WAITING_FOR_HUMAN_INPUT"
            conditions.append(StateCondition(
                status="WAITING_FOR_HUMAN_INPUT",
                reason_code="HUMAN_AUTHORITY_REQUIRED",
                message="Problem formulation requires human input or authority."
            ))
        else:
            # 3. Problem -> Structured Problem & Execution Plan
            try:
                structured_problem, execution_plan = self.structurer.build_network(problem)
                problem.structured_problem = structured_problem
                
                # Check evidence requirements from both semantic and structural proposals
                all_evidence = set(problem.evidence_requirements) | set(structured_problem.evidence_requirements)
                if len(all_evidence) > 0:
                    # LS60: evidence is OPTIONAL — record it as informational, do not block/WAIT.
                    conditions.append(StateCondition(
                        status="INFORMATIONAL",
                        reason_code="EVIDENCE_OPTIONAL",
                        message=f"Optional evidence suggested: {', '.join(all_evidence)}"
                    ))
                elif len(execution_plan.steps) == 0:
                    status = "BLOCKED"
                    conditions.append(StateCondition(
                        status="BLOCKED",
                        reason_code="NO_TASKS_STRUCTURED",
                        message="Structurer could not formulate a valid execution plan from tasks."
                    ))
            except RuntimeError as e:
                # If Structurer fails closed (cycles, bad owners, etc.)
                status = "FAILED"
                conditions.append(StateCondition(
                    status="FAILED",
                    reason_code="STRUCTURER_FAILURE",
                    message=str(e)
                ))

        # B3 / LS60(b): deduplicate steps that map to the SAME (canonical_em, capability_id, target).
        # The dynamic LLM plan can propose near-identical tasks (e.g. two EM Descriptor
        # extract_relevant_information steps, or two Prescriptor evaluate_alternatives), which adds
        # redundant execution and can leave the pipeline in an ambiguous state. Keep the FIRST
        # occurrence, drop later duplicates, and rewire any dependents to the kept step.
        if status not in ["FAILED", "BLOCKED"]:
            _dedup_execution_steps(execution_plan)

        # LS52: Guarantee a result-producing Publisher step. LLM-generated plans sometimes end
        # before Publisher (e.g. only Descriptor/Prescriptor), which completes with a result of
        # UNAVAILABLE ("No actionable execution output"). Inject a Publisher so every Work yields
        # a final published answer. The Publisher compiles the result from the canonical state
        # (knowledge findings, prescription, execution state) and needs no frozen asset (LS48).
        if status not in ["FAILED", "BLOCKED"] and len(execution_plan.steps) > 0 \
                and not any(step.produces_result for step in execution_plan.steps):
            from .problem_model import CognitiveTask
            dep_ids = [s.step_id for s in execution_plan.steps]
            # Add a matching CognitiveTask (owner "EM Publisher") so the runtime dispatches this
            # step to EMPublisher (the dispatch looks up a task by step_id with owner == EM Publisher).
            if problem.structured_problem and problem.structured_problem.task_network:
                problem.structured_problem.task_network.tasks.append(CognitiveTask(
                    task_id="task_publish",
                    description="Generate the final published summary of the work",
                    owner="EM Publisher",
                    expected_outputs=["Final published summary"],
                    dependencies=dep_ids
                ))
            execution_plan.steps.append(ExecutionStep(
                step_id="task_publish",
                capability_id="generate_summary",
                target="EM[PUBLISHER]",
                canonical_em="EM Publisher",
                status="PENDING",
                dependencies=dep_ids,
                expected_outputs=["Final published summary of the work"],
                produces_result=True,
                provenance=["Orchestrator injected Publisher to guarantee a final result"]
            ))

        # LS63: Enforce the canonical EM-pipeline order so a malformed LLM plan cannot deadlock.
        # Some plans list a LATER EM before an EARLIER one (e.g. EM Actioner before EM Prescriptor),
        # so the Actioner runs, finds no prescription, and waits on evidence forever while the
        # Prescriptor stays PENDING behind it. This rewires dependencies to respect EM rank:
        # a step only depends on strictly-lower-rank EMs (and its own intra-EM deps), which
        # guarantees Prescriptor precedes Actioner and removes the deadlock.
        self._normalize_em_pipeline_order(execution_plan)

        for step in execution_plan.steps:
            if step.canonical_em and step.canonical_em not in work.selected_ems:
                work.selected_ems.append(step.canonical_em)
        
        # 4. Build Visualization Manifest dynamically from knowledge state
        visualizations = []
        visualizations.append(VisualizationBinding(id="Inspector"))
        
        targets = [step.target for step in execution_plan.steps]
        
        # Populate deprecated flat arrays for legacy WorkRuntime support
        resolved_pipeline = [step.capability_id for step in execution_plan.steps]
        gaps = []
        
        if any("SCIENTIFIC" in t for t in targets):
            visualizations.append(VisualizationBinding(id="Scientific Surface"))
            
        if any("RANKING" in t for t in targets) or any("ACFLEngine" in t for t in targets):
            visualizations.append(VisualizationBinding(id="Decision Field"))
            visualizations.append(VisualizationBinding(id="Phase Space"))
            visualizations.append(VisualizationBinding(id="Compensation Surface", data_source="canonical.acfl.frontier"))
            
        if any("StoryEngine" in t for t in targets):
            visualizations.append(VisualizationBinding(id="Story Canvas"))
            
        if any("VisualizationEngine" in t for t in targets):
            visualizations.append(VisualizationBinding(id="Intelligence Network"))

        # 5. Build Canonical State
        canonical_state = CanonicalWorkState(
            work=work,
            problem=problem,
            execution_plan=execution_plan,
            resolved_pipeline=resolved_pipeline,
            gaps=gaps,
            conditions=conditions,
            status=status,
            visualizations=visualizations,
            problem_state=problem.status
        )

        # Loop 83: EM Core `core_analysis` — READ-ONLY projection of the orchestration.
        canonical_state.core_analysis = build_core_analysis(canonical_state)

        # LS77.1: EM Core provenance / traceability. Assign a stable problem_id if the
        # model did not set one, and record the EM Core runtime invocation (candidate ->
        # governance) so the ProblemModel stays traceable end-to-end.
        if not problem.problem_id:
            problem.problem_id = f"PROB-{uuid.uuid4().hex[:8].upper()}"
            canonical_state.problem.problem_id = problem.problem_id
        try:
            record_runtime_call(
                canonical_state, em="EM Core", capability_id="propose_problem",
                call_id=f"CALL-{uuid.uuid4().hex[:8]}",
                model=getattr(self.interpreter.engine, "model", None) or self.interpreter.engine.__class__.__name__,
                output_schema="ProblemModel", status="COMPLETED",
                context_id=work.work_id,
            )
        except Exception:
            pass  # telemetry never breaks the pipeline

        # LS77.1 authority HITL gate: if the problem requires human authority, create a real
        # (non-decision) HumanInteractionRequest so the pipeline pauses on a governed HITL
        # point. A HumanDecisionPoint is NOT created here — the Prescriptor owns the
        # decision (F-2 keeps exactly 1 decision point).
        if getattr(problem, "authority_status", "UNDETERMINED") == "HUMAN_REQUIRED":
            from .canonical_state import HumanInteractionRequest
            canonical_state.human_requests.append(HumanInteractionRequest(
                type="HUMAN_AUTHORITY",
                question="Se requiere autoridad humana para aprobar este problema.",
                reason="EM Core detectó que el problema requiere autoridad humana explícita (clasificación Python, no LLM).",
                required_information=["AUTHORITY"],
                decision_required=False,
                blocking=True,
            ))

        return canonical_state

    # Canonical 8-EM ordering used to normalize plan execution order.
    _EM_PIPELINE_ORDER = [
        "EM Core", "EM Structurer", "EM Descriptor", "EM Predictor",
        "EM Prescriptor", "EM Actioner", "EM Installer", "EM Publisher",
    ]

    def _normalize_em_pipeline_order(self, execution_plan) -> None:
        """Rewire step dependencies so NO step runs before a LATER-EM prerequisite.

        For each step we keep only deps on same-EM (intra) steps and on strictly
        lower-EM-rank steps, then add every strictly-lower-rank step as a dependency.
        Because a step ends up depending only on strictly-lower-rank steps (and its own
        EM), the resulting graph is acyclic and respects the canonical EM order — so a
        Prescriptor always precedes an Actioner, regardless of the LLM plan's ordering.
        Steps with an unknown/empty EM keep their dependencies untouched (no-op).
        """
        steps = list(execution_plan.steps)
        order = {name: i for i, name in enumerate(self._EM_PIPELINE_ORDER)}

        def _rank(s):
            em = getattr(s, "canonical_em", None)
            if em in order:
                return order[em]
            return 99 if em else None

        ranks = {s.step_id: _rank(s) for s in steps}

        for s in steps:
            r = ranks[s.step_id]
            if r is None or r == 99:
                continue  # unknown/empty EM — leave as-is
            keep: list = []
            for d in list(s.dependencies):
                dr = ranks.get(d, 99)
                if dr is None:
                    dr = 99  # unknown/empty-EM dependency → treat as "after all", never a back-edge
                # Keep intra-EM and lower-rank deps; drop backward (higher-rank) deps.
                if dr <= r and d not in keep:
                    keep.append(d)
            # Add every strictly-lower-rank step so the EM order is enforced.
            for other in steps:
                if other.step_id == s.step_id:
                    continue
                orr = ranks.get(other.step_id, 99)
                if orr is not None and orr < r and other.step_id not in keep:
                    keep.append(other.step_id)
            s.dependencies = keep
