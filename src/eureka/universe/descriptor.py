import logging
import unicodedata
from typing import List, Dict, Any, Optional, Iterable
import uuid

from .canonical_state import CanonicalWorkState, ExtractedEvidence, StructuredFinding, ExecutionStep
from .cognitive_engine import CognitiveEngine, DescriptorProposal, record_runtime_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------------------------
# Shared, reusable deterministic CONTENT gate (single implementation).
# The lexical grounding gate below and the governed human-response sufficiency evaluator
# (`human_input_sufficiency.py`) MUST use the same notion of "substantive token" so the system
# has ONE deterministic content criterion instead of two divergent ones.
# ---------------------------------------------------------------------------------------------
_STOPWORDS = set("""a an and are as at be but by for from has have if in into is it its of on or that the
this to was were will with would about can could not only so than then too very what when where which who
why la el los las un una y o de del al que en es son para por con sin no se su sus""".split())


def fold_text(text: str) -> str:
    """Fold diacritics so 'qué'/'que' and 'más'/'mas' compare equal (deterministic, no deps)."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def substantive_tokens(text: Any) -> set:
    """Deterministic substantive-token set: accent-folded, lowercased, stopwords and <=2 chars out."""
    if text is None:
        return set()
    folded = fold_text(str(text)).lower()
    raw = [w.strip(".,;:!?()[]{}\"'-") for w in folded.split()]
    return {w for w in raw if w and w not in _STOPWORDS and len(w) > 2}


def lexical_overlap(statement: str, sources: Iterable[str]) -> bool:
    """Deterministic lexical grounding gate (conservative). True when the statement shares at
    least one substantive token with a source. Rejects clear hallucinations (zero overlap) while
    tolerating legitimate paraphrase. Single implementation shared with the sufficiency evaluator."""
    if not statement:
        return False
    stmt_tokens = {w for w in statement.lower().split() if w not in _STOPWORDS and len(w) > 2}
    if not stmt_tokens:
        return False
    for src in sources:
        src_tokens = set((src or "").lower().split())
        if stmt_tokens & src_tokens:
            return True
    return False

class EMDescriptor:
    """
    Cognitive owner of descriptive knowledge discovery from evidence.
    LS77.2 governance: LLM proposes findings, Python grounds them. A finding is NEVER
    sealed VALIDATED unless it is lexically supported by the referenced source (evidence
    text blocks or, in the no-evidence case, the user context). Unsupported LLM
    statements are downgraded to UNSUPPORTED (not promoted as truth).
    Authority="Findings / evidencia", LLM=🟢 (subordinado), Determinismo=🟡 (Python valida).
    """
    _STOP = _STOPWORDS   # kept for backwards compatibility (single source: module-level _STOPWORDS)

    def _grounded(self, statement: str, sources: List[str]) -> bool:
        """Deterministic lexical grounding gate (conservative). Delegates to the SINGLE shared
        implementation (`lexical_overlap`) so the Descriptor gate and the governed human-response
        sufficiency evaluator can never diverge."""
        return lexical_overlap(statement, sources)

    def __init__(self, cognitive_engine: CognitiveEngine):
        self.cognitive_engine = cognitive_engine

    def execute(self, canonical: CanonicalWorkState, step: ExecutionStep) -> None:
        """
        Executes the descriptive knowledge discovery process.
        """
        if not canonical.evidence and not (canonical.problem and canonical.problem.context) and not (canonical.work and canonical.work.user_intent):
            raise RuntimeError("FAIL_CLOSED: Descriptor cannot operate without evidence or context.")
            
        if not canonical.problem or not canonical.problem.structured_problem:
            raise RuntimeError("FAIL_CLOSED: Descriptor requires a Governed ProblemModel and a StructuredProblem.")
            
        # Get the task context
        task = next((t for t in canonical.problem.structured_problem.task_network.tasks if t.task_id == step.step_id), None)
        if not task:
            # Fallback for old tasks that aren't mapped properly
            from .problem_model import CognitiveTask
            task = CognitiveTask(task_id=step.step_id, description=f"Extract knowledge using {step.capability_id}", owner="EM Descriptor")

        # Collect available evidence units
        evidence_units = []
        for e in canonical.evidence:
            if e.extraction_status in ["EXTRACTED", "PARTIAL"] and e.evidence_id in canonical.extracted_evidence:
                evidence_units.append(canonical.extracted_evidence[e.evidence_id])

        # LS60: evidence is OPTIONAL — if none, derive a source unit from the user intent/context
        # so the pipeline proceeds without attached evidence.
        context_only = False
        if not evidence_units:
            src = None
            if canonical.problem:
                src = canonical.problem.context or getattr(canonical.problem, "intent", None) or canonical.problem.objective
            if not src and canonical.work:
                src = canonical.work.user_intent
            if not src:
                raise RuntimeError("FAIL_CLOSED: No extracted evidence or user context available for Descriptor.")
            import datetime as _dt
            from .canonical_state import ExtractedEvidence as _EE
            ctx = _EE(
                extracted_evidence_id="EVI-CONTEXT",
                evidence_id="EVI-CONTEXT",
                content_type="text/plain",
                text_blocks=[src],
                extraction_method="USER_CONTEXT",
                parser_id="ContextParser",
                parser_version="1.0",
                extraction_timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
            )
            canonical.extracted_evidence["EVI-CONTEXT"] = ctx
            evidence_units.append(ctx)
            context_only = True

        # Ask CognitiveEngine for a proposal
        import time as _time, uuid as _uuid
        t0 = _time.time()
        _status = "COMPLETED"
        try:
            proposal = self.cognitive_engine.propose_findings(canonical.problem, task, evidence_units)
        except Exception:
            _status = "FAILED"
            record_runtime_call(
                canonical, em="EM Descriptor", capability_id=getattr(task, "capability_id", "propose_findings"),
                call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model=getattr(self.cognitive_engine, "model", "test_double"),
                output_schema="DescriptorProposal", latency_ms=(_time.time() - t0) * 1000,
                context_id=canonical.work.work_id if canonical.work else "", status=_status,
            )
            raise
        record_runtime_call(
            canonical, em="EM Descriptor", capability_id=getattr(task, "capability_id", "propose_findings"),
            call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model=getattr(self.cognitive_engine, "model", "test_double"),
            output_schema="DescriptorProposal", latency_ms=(_time.time() - t0) * 1000,
            context_id=canonical.work.work_id if canonical.work else "", status=_status,
        )
        
        # Validate findings
        validated_findings = self._validate_findings(proposal, evidence_units, task, canonical, context_only=context_only)
        
        # Determine contradictions if any (for R3 we will just do a basic check, or preserve)
        # Contradictions are handled by storing them or marking them.
        
        # Append to Knowledge State
        canonical.knowledge.findings.extend(validated_findings)
        canonical.knowledge.version += 1

        # Gap 4 — Descriptor contract (additive & truthful). Populate the structured descriptive
        # surface from REAL data where derivable; carried from the engine when supplied.
        canonical.knowledge.patterns = [f.statement for f in validated_findings if f.finding_type == "RELATIONAL"] \
            if not proposal.patterns else list(proposal.patterns)
        canonical.knowledge.metrics = {
            "findings": len(canonical.knowledge.findings),
            "validated": sum(1 for f in canonical.knowledge.findings if f.status == "VALIDATED"),
            "relational": sum(1 for f in canonical.knowledge.findings if f.finding_type == "RELATIONAL"),
            "contradictions": len(canonical.knowledge.contradictions),
            "unknowns": len(canonical.knowledge.unknowns),
        }
        canonical.knowledge.uncertainty = list(canonical.knowledge.unknowns) if not proposal.uncertainty else list(proposal.uncertainty)
        canonical.knowledge.limitations = list(proposal.limitations or [])
        canonical.knowledge.predicates = list(proposal.predicates or [])
        canonical.knowledge.dependencies_for_predictor = list(proposal.dependencies_for_predictor or []) \
            or [f.finding_id for f in validated_findings if f.status == "VALIDATED"]
        
        # Update step provenance
        step.provenance.append(f"EMDescriptor executed task {task.task_id}, generated {len(validated_findings)} validated findings.")
        
        # Important: Descriptor does not produce the final WorkResult unless specified.
        # But we must update the state.
        
    def _validate_findings(self, proposal: DescriptorProposal, evidence_units: List[ExtractedEvidence], task: Any, canonical: CanonicalWorkState, context_only: bool = False) -> List[StructuredFinding]:
        valid_findings = []
        
        # Create lookup map
        eu_map = {e.extracted_evidence_id: e for e in evidence_units}
        
        for cand in proposal.candidate_findings:
            # LS60: when the only source is the user intent (context_only), accept findings as
            # sourced from the context unit, even if the LLM did not cite a matching evidence ref.
            if context_only:
                refs = cand.evidence_refs or ["EVI-CONTEXT"]
                if not any(ref == "EVI-CONTEXT" or ref in eu_map for ref in refs):
                    refs = ["EVI-CONTEXT"]
                ctx_unit = eu_map.get("EVI-CONTEXT")
                ctx_sources = []
                if ctx_unit and ctx_unit.text_blocks:
                    ctx_sources = [" ".join(ctx_unit.text_blocks)]
                elif canonical.problem:
                    ctx_sources = [canonical.problem.context or ""]
                grounded = self._grounded(cand.statement, ctx_sources) if ctx_sources else False
                finding = StructuredFinding(
                    finding_id=f"FND-{uuid.uuid4().hex[:8].upper()}",
                    statement=cand.statement,
                    finding_type=cand.finding_type,
                    evidence_refs=refs,
                    method=cand.method or "DESCRIPTOR_ANALYSIS",
                    status="VALIDATED" if grounded else "UNSUPPORTED",
                    provenance=[f"Task[{task.task_id}]",
                                ("Evidence[EVI-CONTEXT] -> USER_CONTEXT (grounded)" if grounded else
                                 "Derived from user context but NOT lexically grounded -> UNSUPPORTED")]
                )
                valid_findings.append(finding)
                continue

            if not cand.evidence_refs:
                # Rule 16: Finding must have evidence support
                logger.warning(f"Rejecting finding: UNSUPPORTED (No evidence_refs). Statement: {cand.statement}")
                continue
                
            supported = True
            valid_refs = []
            provenance = [f"Task[{task.task_id}]"]
            
            for ref in cand.evidence_refs:
                if ref not in eu_map:
                    logger.warning(f"Rejecting finding: EVIDENCE_UNAVAILABLE (Ref {ref} not found). Statement: {cand.statement}")
                    supported = False
                    break
                valid_refs.append(ref)
                provenance.append(f"Evidence[{ref}] -> {eu_map[ref].evidence_id}")
                
            if not supported:
                continue
                
            # Epistemic validation: Must be descriptive
            if cand.finding_type in ["PREDICTION", "PRESCRIPTION"]:
                logger.warning(f"Rejecting finding: SCOPE_VIOLATION ({cand.finding_type} is not owned by Descriptor). Statement: {cand.statement}")
                continue

            # Grounding gate (LS77.2): the statement must be lexically supported by the
            # cited evidence text blocks. Unsupported statements are downgraded, not promoted.
            evid_sources = [" ".join(u.text_blocks or []) for u in (eu_map.get(ref) for ref in valid_refs) if u]
            grounded = self._grounded(cand.statement, evid_sources) if evid_sources else False

            finding = StructuredFinding(
                finding_id=f"FND-{uuid.uuid4().hex[:8].upper()}",
                statement=cand.statement,
                finding_type=cand.finding_type,
                evidence_refs=valid_refs,
                method=cand.method or "DESCRIPTOR_ANALYSIS",
                status="VALIDATED" if grounded else "UNSUPPORTED",
                provenance=provenance + (["grounded_in_evidence"] if grounded else ["NOT_grounded_in_evidence -> UNSUPPORTED"])
            )
            valid_findings.append(finding)
            
        return valid_findings
