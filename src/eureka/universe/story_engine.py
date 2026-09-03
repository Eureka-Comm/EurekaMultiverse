from typing import Dict, Any, List
from .canonical_state import CanonicalWorkState

def _ns(v):
    """None-safe: return '' for None to avoid str(None)/join errors."""
    return v if v is not None else ""

class StoryEngine:
    """
    LS85 — Governed Cognitive Storytelling. Produces a narrative that is a FAITHFUL
    projection of the GOVERNED canonical state (not independent semantic generation).

    Key authority rule:
      - DECISION comes ONLY from human_decision (human_selection + decision_id + authority).
      - NEVER from recommendation / recommended_option / LLM narrative.
      - If no human decision exists -> "DECISION PENDING" (never invent one).

    Each act carries:
      phase          -> narrative act name
      content        -> human-readable text grounded in the state
      source         -> governing artifact id (FND-*/PRED-*/PRESC-*/DEC-*/AP-*/EXEC-*/WR-*) or NOT_AVAILABLE
      authority      -> LLM_CANDIDATE | VALIDATED | NOT_EVALUATED | HUMAN_AUTHORIZED | SIMULATED | GAP
    """
    def generate_story(self, state: CanonicalWorkState):
        arc: List[Dict[str, Any]] = []

        def add(phase, content, source, authority):
            arc.append({
                "phase": phase,
                "content": content,
                "source": source,
                "authority": authority,
            })

        prob = state.problem
        # QUESTION
        if prob:
            add("THE QUESTION", _ns(getattr(prob, "objective", "")),
                _ns(getattr(prob, "problem_id", None)) or "NOT_AVAILABLE",
                "LLM_CANDIDATE")

            # CONTEXT / EVIDENCE
            ev_findings = [f for f in (getattr(state.knowledge, "findings", None) or [])]
            if ev_findings:
                add("WHAT THE EVIDENCE SAYS",
                    "Se identificaron %d hallazgos sobre la evidencia disponible." % len(ev_findings),
                    "FINDINGS", "VALIDATED" if any(getattr(f, "status", None) == "VALIDATED" for f in ev_findings) else "GAP")

            # FINDING (individual, traceable)
            for f in ev_findings[:4]:
                add("FINDING", _ns(getattr(f, "statement", ""))[:200],
                    _ns(getattr(f, "finding_id", None)) or "NOT_AVAILABLE",
                    getattr(f, "status", "UNSUPPORTED"))

        # PREDICTION (governed math)
        pk = state.predictive_knowledge
        predicates = [p for p in (getattr(pk, "predicates", None) or [])]
        if predicates:
            add("PREDICTION",
                "El motor matemático (ACFL_DETERMINISTIC, GCLV Eq 4.17) evaluó %d predicado(s)." % len(predicates),
                "PREDICATES", "VALIDATED")
        for p in predicates[:2]:
            add("PREDICTION", "Predicado GCLV sobre '%s' (mse=%s)." % (_ns(getattr(p, "target", "")), _ns(getattr(p, "mse", None))),
                _ns(getattr(p, "predicate_id", None)) or "NOT_AVAILABLE",
                "VALIDATED" if getattr(p, "status", None) == "VALIDATED" else "NOT_EVALUATED")

        # PRESCRIPTION / ALTERNATIVES
        prk = state.prescriptive_knowledge
        prescriptions = [v for v in (getattr(prk, "prescriptions", None) or [])]
        presc = prescriptions[-1] if prescriptions else None
        if presc:
            alts = [a for a in (getattr(presc, "alternatives", None) or [])]
            add("PRESCRIPTION",
                "El Prescriptor generó %d alternativa(s) candidata(s); %s." % (
                    len(alts), "la autoridad de selección es humana (HITL)." if getattr(presc, "human_decision_required", False) else "provisional."),
                _ns(getattr(presc, "prescription_id", None)) or "NOT_AVAILABLE",
                "HUMAN_AUTHORIZED" if getattr(presc, "authority", None) == "HUMAN" else "LLM_CANDIDATE")

        # DECISION — ONLY from human_decision (never recommendation)
        hd = getattr(state, "human_decision", None)
        if hd and getattr(hd, "selected_alternative_id", None):
            add("THE DECISION",
                "El humano autorizó la alternativa %s (%s)." % (_ns(getattr(hd, "selected_alternative_id", None)), _ns(getattr(hd, "decision_id", None))),
                _ns(getattr(hd, "decision_id", None)) or "NOT_AVAILABLE",
                "HUMAN_AUTHORIZED")
        else:
            add("THE DECISION", "La decisión está pendiente — el sistema no inventa una selección.",
                "DECISION_PENDING", "PENDING")

        # ACTION PLAN
        ap = getattr(state, "action_plan", None)
        if ap:
            add("ACTION",
                "Plan %s (%s acciones) derivado de la decisión autorizada; validado por gates gobernados (NO ejecución autónoma)." % (
                    _ns(getattr(ap, "plan_id", None)), len(getattr(ap, "actions", None) or [])),
                _ns(getattr(ap, "plan_id", None)) or "NOT_AVAILABLE",
                getattr(ap, "validation_status", "UNVERIFIED"))

        # EXECUTION — SIMULATED (never claimed as external)
        es = getattr(state, "execution_state", None)
        if es:
            add("EXECUTION",
                "El Installer produjo una ejecución %s." % "SIMULADA (Level 1/2, no externa)." if getattr(es, "status", None) else "pendiente",
                "EXECUTION", "SIMULATED")

        # RESULT
        res = getattr(state, "result", None)
        if res and getattr(res, "status", None) == "AVAILABLE":
            add("THE RESULT", _ns(getattr(res, "summary", "")),
                _ns(getattr(res, "result_id", None)) or "NOT_AVAILABLE",
                "PUBLISHED")

        state.extracted_entities["story_arc"] = arc
        return arc
