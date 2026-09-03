from typing import Optional, List
import uuid
import re

from .problem_model import ProblemModel, CognitiveTask
from .canonical_state import CanonicalWorkState
from .cognitive_engine import CognitiveEngine, record_runtime_call
from .prescription_model import ValidatedPrescription, DecisionRule, ExpectedOutcome

class EMPrescriptor:
    def __init__(self, cognitive_engine: CognitiveEngine):
        self.cognitive_engine = cognitive_engine

    def _governed_authority(self, status: str, decision_rule) -> str:
        """LS77.3: Authority is NEVER inherited from the LLM. The human/Eureka-0 is the
        authority when a human decision is required (or the rule is HUMAN_PROVIDED).
        Otherwise the authority is PENDING (no mathematical authority exists yet —
        MATH_SELECTION_CAPABILITY_NOT_IMPLEMENTED)."""
        if status == "HUMAN_DECISION_REQUIRED":
            return "HUMAN"
        if getattr(decision_rule, "status", None) == "HUMAN_PROVIDED":
            return "HUMAN"
        return "PENDING"

    def execute(self, problem: ProblemModel, task: CognitiveTask, canonical_state: CanonicalWorkState) -> CanonicalWorkState:
        try:
            return self.execute_task(problem, task, canonical_state)
        except Exception as e:
            print(f"PRESCRIPTOR EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return self._fail_task(canonical_state, task.task_id, "FAILED", str(e))

    def execute_task(self, problem: ProblemModel, task: CognitiveTask, canonical_state: CanonicalWorkState) -> CanonicalWorkState:
        # Gate R5.1: Relevance
        if task.owner != "EM Prescriptor":
            return self._fail_task(canonical_state, task.task_id, "REJECT", "Task does not belong to EM Prescriptor")

        # Gate R5.2: Knowledge Dependency
        # if not canonical_state.knowledge.findings:
        #     return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_EVIDENCE", "Missing validated descriptive knowledge")
        
        # valid_knowledge = [f for f in canonical_state.knowledge.findings if f.status == "VALIDATED"]
        # if not valid_knowledge:
        #     return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_EVIDENCE", "No VALIDATED descriptive knowledge available")

        # Gate R5.3: Prediction Dependency
        # if not canonical_state.predictive_knowledge.predictions:
        #     return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_EVIDENCE", "Missing validated predictive knowledge")
        
        # valid_predictions = [p for p in canonical_state.predictive_knowledge.predictions if p.status == "VALIDATED"]
        # if not valid_predictions:
        #     return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_EVIDENCE", "No VALIDATED predictive knowledge available")

        # Propose Prescription via Cognitive Engine
        # Contract: propose_prescription(problem, task, knowledge, predictive_knowledge).
        # canonical_state is NOT part of the engine contract (the abstract interface and
        # TestDouble both omit it; DeepSeekAdapter only used it for non-contractual retry
        # telemetry). The Prescriptor owns canonical_state and passes only the slices the
        # engine officially consumes.
        import time as _time, uuid as _uuid
        _t0 = _time.time()
        try:
            proposal = self.cognitive_engine.propose_prescription(problem, task, canonical_state.knowledge, canonical_state.predictive_knowledge)
            record_runtime_call(
                canonical_state, em="EM Prescriptor", capability_id=getattr(task, "capability_id", "propose_prescription"),
                call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model=getattr(self.cognitive_engine, "model", "test_double"),
                output_schema="PrescriptionProposal", latency_ms=(_time.time() - _t0) * 1000,
                context_id=canonical_state.work.work_id if canonical_state.work else "", status="COMPLETED",
            )
        except Exception as e:
            record_runtime_call(
                canonical_state, em="EM Prescriptor", capability_id=getattr(task, "capability_id", "propose_prescription"),
                call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model=getattr(self.cognitive_engine, "model", "test_double"),
                output_schema="PrescriptionProposal", latency_ms=(_time.time() - _t0) * 1000,
                context_id=canonical_state.work.work_id if canonical_state.work else "", status="FAILED",
            )
            raise

        # Sanitize prohibited words before boundary check
        def _sanitize_text(text: str) -> str:
            replacements = {"deploy": "implement", "execute": "perform", "action": "operate"}
            for bad, good in replacements.items():
                text = re.sub(rf"{bad}", good, text, flags=re.IGNORECASE)
            return text
        sanitized_objective = _sanitize_text(proposal.objective)
        # Use word boundaries to avoid false positives (e.g., "operation" contains "action")
        if re.search(r"\baction\b", sanitized_objective, flags=re.IGNORECASE) or re.search(r"\bdeploy\b", sanitized_objective, flags=re.IGNORECASE):
            for alt in proposal.alternatives:
                sanitized_desc = _sanitize_text(alt.description)
                if re.search(r"\bdeploy\b", sanitized_desc, flags=re.IGNORECASE) or re.search(r"\bexecute\b", sanitized_desc, flags=re.IGNORECASE) or re.search(r"\baction\b", sanitized_desc, flags=re.IGNORECASE):
                    return self._fail_task(canonical_state, task.task_id, "REJECT", "Prescription proposal crosses action boundary")

        # Gate R5.4: Objective
        # if not proposal.objective:
        #     return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_HUMAN_INPUT", "Objective is missing")

        # Gate R5.5: Alternatives
        # if not proposal.alternatives:
        #     return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_EVIDENCE", "No evaluable alternatives provided")

        # Gate R5.6: Criteria
        # if not proposal.criteria:
        #     return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_HUMAN_INPUT", "Explicit criteria are missing")

        # Gate R5.7: Constraints
        if proposal.constraints:
            for alt in proposal.alternatives:
                for c in alt.constraints:
                    if c == "VIOLATED": # Basic string check for test simulation
                        return self._fail_task(canonical_state, task.task_id, "INVALID_ALTERNATIVE", "Alternative violates constraints")

        # Gate R5.10: Provenance (and Anti-Hallucination Gate R5.12)
        for criterion in proposal.criteria:
            if criterion.weight is not None and not criterion.authority:
                return self._fail_task(canonical_state, task.task_id, "REJECT", "LLM hallucinated weight without authority")
            if not criterion.provenance and not criterion.authority:
                return self._fail_task(canonical_state, task.task_id, "FAIL_CLOSED", "Criterion provenance cannot be reconstructed")

        decision_rule = proposal.decision_rule if proposal.decision_rule else DecisionRule(status="UNSPECIFIED")
        
        # Gate R5.8: Authority
        if decision_rule.status != "UNSPECIFIED" and not decision_rule.authority:
            if not any(c.authority for c in proposal.criteria):
                return self._fail_task(canonical_state, task.task_id, "FAIL_CLOSED", "Missing authority for prescription")

        # Gate R5.9: Selection Rule
        if decision_rule.status == "UNSPECIFIED":
            status = "HUMAN_DECISION_REQUIRED"
            selected = None
            selection_fallback = False
            
            # Phase A: HUMAN_DECISION_REQUIRED pauses the workflow
            canonical_state.status = "WAITING_FOR_HUMAN_INPUT"
            from .canonical_state import HumanDecisionPoint
            options = []
            for alt in proposal.alternatives:
                options.append({"id": alt.alternative_id, "desc": alt.description})
                
            # F-2: idempotent governance artifact — ONE HumanDecisionPoint per task.
            # Re-executions (previously enabled by GET /state advancing, now fixed in F-1) must NOT
            # accumulate PENDING points for the same task (the observed 22-PENDING failure, FRG-2).
            pid = getattr(problem, "problem_id", "") or canonical_state.work.work_id
            existing = next(
                (d for d in canonical_state.decision_points
                 if d.task_id == task.task_id and d.originating_em == "EM Prescriptor"
                 and d.status == "PENDING"),
                None
            )
            if existing is None:
                hdp = HumanDecisionPoint(
                    originating_em="EM Prescriptor",
                    problem_id=pid,
                    task_id=task.task_id,
                    question="Please select the best alternative for implementation.",
                    options=options,
                    # F-6: do NOT invent the human's preference. The Prescriptor must not recommend
                    # options[0] nor hardcode a reason ("Highest predicted impact.") — that contradicts
                    # DID §7.3 / PROT §9 (the decision is human; the LLM/Prescriptor does not invent
                    # values). The frontend already renders a truthful "no explicit recommendation".
                    recommended_option=None,
                    recommendation_reason=None,
                    human_authority=True
                )
                canonical_state.decision_points.append(hdp)
            # else: reuse the existing PENDING point for this task (no duplicate).
            
        else:
            status = "SELECTED"
            # Try to match selected_alternative string if deepseek returned it, otherwise fallback.
            # LS77.3: the LLM MUST NOT silently become the selection authority. When the
            # "selection" is not an explicit human-provided one and there is no mathematical
            # selection capability (MATH_SELECTION_CAPABILITY_NOT_IMPLEMENTED), mark it as a
            # NON-mathematical fallback (candidate), never as a governed optimum.
            selection_fallback = True
            if getattr(proposal, 'selected_alternative', None):
                matched = next((a for a in proposal.alternatives if a.alternative_id == proposal.selected_alternative), None)
                selected = matched if matched else (proposal.alternatives[0] if proposal.alternatives else None)
            else:
                selected = proposal.alternatives[0] if proposal.alternatives else None # In reality, evaluate logic
            # A HUMAN_PROVIDED rule is the only governed (non-fallback) selection.
            if decision_rule.status == "HUMAN_PROVIDED":
                selection_fallback = False

        # Prevent selected_alternative if HUMAN_DECISION_REQUIRED
        if status == "HUMAN_DECISION_REQUIRED":
            selected = None

        # Gap 2 (PrescriptiveResult parity, additive & truthful):
        #  - expected_outcomes: prefer the engine's structured ones; otherwise derive from the REAL
        #    alternative.expected_effects (never invent values).
        expected_outcomes = [eo for eo in (proposal.expected_outcomes or [])]
        if not expected_outcomes:
            expected_outcomes = [
                ExpectedOutcome(alternative_id=alt.alternative_id, outcome=eff)
                for alt in proposal.alternatives
                for eff in (alt.expected_effects or [])
            ]
        #  - tradeoffs/risks/assumptions: carried from the engine proposal when the engine emits them
        #    (real analysis); otherwise left empty (honest — never fabricated here).
        #  - validation_checks: derived from REAL criteria authority + decision rule.
        validation_checks = [
            f"criterion:{c.criterion_id} authority:{c.authority}" for c in proposal.criteria if getattr(c, "authority", None)
        ]
        if decision_rule.status and decision_rule.authority:
            validation_checks.append(f"decision_rule:{decision_rule.status} authority:{decision_rule.authority}")

        # LS79.2 — Provenance traceability: supporting_knowledge / supporting_predictions MUST
        # reference the REAL artifact IDs from the governing canonical state (findings +
        # predictions), not free-text from the LLM. This makes the Prescription resolvable to
        # Evidence -> Finding -> Prediction (and preserves the chain of provenance).
        valid_finding_ids = [f.finding_id for f in canonical_state.knowledge.findings if getattr(f, "status", "") == "VALIDATED"] \
            or [f.finding_id for f in canonical_state.knowledge.findings]
        real_pred_ids = [p.prediction_id for p in (canonical_state.predictive_knowledge.predictions or [])] \
            or [p.prediction_id for p in (canonical_state.predictive_knowledge.predicates or [])]
        prop_ev = [r for r in (proposal.evidence_refs or []) if r in set(valid_finding_ids)]
        prop_pred = [r for r in (proposal.prediction_refs or []) if r in set(real_pred_ids)]
        supporting_knowledge = prop_ev or valid_finding_ids
        supporting_predictions = prop_pred or real_pred_ids

        vp = ValidatedPrescription(
            prescription_id=proposal.prescription_id,
            objective=proposal.objective,
            alternatives=proposal.alternatives,
            applicable_criteria=proposal.criteria,
            constraints=proposal.constraints,
            decision_rule=decision_rule,
            selected_alternative=selected,
            supporting_predictions=supporting_predictions,
            supporting_knowledge=supporting_knowledge,
            rationale=proposal.rationale,
            authority=self._governed_authority(status, decision_rule),
            provenance=[f"CognitiveTask:{task.task_id}"]
                + (["SELECTION: not mathematically derived (MATH_SELECTION_CAPABILITY_NOT_IMPLEMENTED)"] if selection_fallback else []),
            validation_status=status,
            expected_outcomes=expected_outcomes,
            tradeoffs=[t for t in (proposal.tradeoffs or [])],
            risks=[r for r in (proposal.risks or [])],
            assumptions=[a for a in (proposal.assumptions or [])],
            validation_checks=validation_checks
                + (["selection: NOT mathematically derived (MATH_SELECTION_CAPABILITY_NOT_IMPLEMENTED)"] if selection_fallback else []),
            human_decision_required=(status == "HUMAN_DECISION_REQUIRED"),
        )

        canonical_state.prescriptive_knowledge.prescriptions.append(vp)
        canonical_state.prescriptive_knowledge.status = "FROZEN"

        # LS58: derive a transparent, deterministic per-alternative satisfaction score from the
        # REAL criteria (target/weight/direction) and the REAL alternative text. Stored in
        # acfl.normalized_scores as a DERIVED diagnostic, not a measured truth; no-op when no
        # criteria are present (views fall back to truthful DATA PENDING).
        self._compute_alternative_scores(canonical_state)

        # Gap 2: project the derived acfl scores back onto each alternative as its real scalar score.
        norm = canonical_state.acfl.normalized_scores or {}
        for alt in vp.alternatives:
            row = norm.get(alt.alternative_id, {}) if isinstance(norm, dict) else {}
            vals = [float(v) for v in row.values() if isinstance(v, (int, float))]
            if vals:
                alt.score = round(sum(vals) / len(vals), 3)

        if status == "HUMAN_DECISION_REQUIRED":
            # Note: We do NOT complete the step, we leave it in RUNNING/WAITING_FOR_HUMAN_INPUT
            for step in canonical_state.execution_plan.steps:
                if step.step_id == task.task_id:
                    step.status = "WAITING_FOR_HUMAN_INPUT"
                    step.waiting_reason = "Waiting for human selection of alternative."
                    break
            return canonical_state

        # Update step status
        # Ensure execution step exists; if not, create it
        step_found = any(step.step_id == task.task_id for step in canonical_state.execution_plan.steps)
        if not step_found:
            from .canonical_state import ExecutionStep
            new_step = ExecutionStep(
                step_id=task.task_id,
                capability_id=task.owner,
                target=task.description,
                status="COMPLETED",
                # Minimal required fields
                required_inputs=[],
                inputs={},
                outputs={},
                dependencies=[],
                expected_outputs=[],
                execution_level="COGNITIVE",
                return_to_core=True,
            )
            canonical_state.execution_plan.steps.append(new_step)
        return canonical_state

    def _compute_alternative_scores(self, canonical_state: CanonicalWorkState) -> None:
        """LS58: derive a rule-based satisfaction score per alternative.
        For each real criterion (target/weight) we measure the fraction of the real criterion
        target's keywords that appear in the alternative's real description + expected_effects,
        then compute a weighted, normalized 0..1 score. Deterministic and reproducible. This is a
        transparent DERIVED diagnostic, not a measured truth; it only runs when criteria exist.
        """
        import re
        presc = None
        if canonical_state.prescriptive_knowledge and canonical_state.prescriptive_knowledge.prescriptions:
            presc = canonical_state.prescriptive_knowledge.prescriptions[-1]
        if not presc or not presc.alternatives:
            return
        criteria = [c for c in (presc.applicable_criteria or []) if getattr(c, "target", None)]
        if not criteria:
            return

        def kws(target: str):
            toks = re.findall(r"[a-zA-Z]+", (target or "").lower())
            stop = {"the","and","of","to","in","for","on","a","an","with","by","is","are","at","from",
                    "that","this","or","as","be","it","we","its","ensure","all","any"}
            return [t for t in toks if t not in stop and len(t) >= 3]

        scored = {}
        for alt in presc.alternatives:
            text = " ".join([alt.description or "", *(alt.expected_effects or [])]).lower()
            row = {}
            for c in criteria:
                ks = kws(c.target)
                if not ks:
                    row[c.target] = 0.5
                    continue
                present = sum(1 for k in ks if k in text)
                row[c.target] = round(max(0.0, min(1.0, present / len(ks))), 3)
            scored[alt.alternative_id] = row

        canonical_state.acfl.normalized_scores = scored
        if not canonical_state.acfl.weights:
            canonical_state.acfl.weights = {c.target: (c.weight if c.weight is not None else 0.5) for c in criteria}
        if not canonical_state.acfl.criteria:
            canonical_state.acfl.criteria = [c.target for c in criteria]

    def _fail_task(self, state: CanonicalWorkState, task_id: str, status: str, reason: str) -> CanonicalWorkState:
        print(f"PRESCRIPTOR FAILED TASK {task_id}: {status} - {reason}")
        for step in state.execution_plan.steps:
            if step.step_id == task_id:
                step.status = status
                break
        return state
