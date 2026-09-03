import logging
from typing import List, Dict, Any, Optional
import uuid
import hashlib
import json
import re

from .canonical_state import (
    CanonicalWorkState, 
    ExecutionStep, 
    PredictionKnowledge, 
    PredictivePredicate,
    PredictionScenario,
    PredictiveUncertainty
)
from .cognitive_engine import CognitiveEngine, PredictorProposal, CandidatePrediction, record_runtime_call
from .cognitive_engine import InformationSufficiencyProposal, MissingInformationItem
from .acfl_engine import ACFLEngine
from .math_ir import MathematicalExpression, AnyMathematicalExpression
from .metrics import compute_mse

logger = logging.getLogger(__name__)

class EMPredictor:
    """
    EM Predictor — Cognitive Owner of Predictive Knowledge Discovery.
    Transforms validated descriptive knowledge into predictive knowledge using ACFL mathematical foundations.
    Enforces strict mathematical authority boundaries.
    """
    def __init__(self, cognitive_engine: CognitiveEngine):
        self.cognitive = cognitive_engine
        self.engine = ACFLEngine()

    def _generate_signature(self, knowledge_version: int, predicate_dict: dict, inputs: dict) -> str:
        """Gate 20 - Deterministic Prediction Signature"""
        sig_data = {
            "knowledge_version": knowledge_version,
            "predicate": predicate_dict,
            "inputs": inputs,
            "engine_version": "EUREKA_ACFL_V5.1"
        }
        sig_str = json.dumps(sig_data, sort_keys=True)
        return hashlib.sha256(sig_str.encode('utf-8')).hexdigest()

    def _deterministic_propose_predictions(self, state: CanonicalWorkState, task: ExecutionStep) -> PredictorProposal:
        """Deterministic EM Predictor (pure Python/math, NO LLM).

        Builds candidate predictions from numeric variables present in the knowledge base,
        attaching a real ACFL (GCLV) mathematical predicate so the subsequent Python math
        stage (MSE, evaluate_expression) can evaluate it. If there is no numeric input data,
        the proposal is empty and the pipeline marks the predictions NOT_EVALUATED (F-5):
        the predictor never calls an LLM, so it never hangs or fails on a slow model.
        """
        import re
        var_names: set = set()

        def _var_words(text: str):
            for m in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b", text or ""):
                if m.lower() not in {
                    "the", "and", "for", "with", "that", "this", "from", "data", "value", "total",
                    "status", "not", "are", "was", "will", "has", "have", "model", "prediction",
                    "need", "can", "should", "would", "please", "provide", "identify", "using",
                }:
                    var_names.add(m)

        # 1) numeric/quantitative findings
        for f in state.knowledge.findings:
            ft = (f.finding_type or "").upper()
            if any(k in ft for k in ("QUANTITATIVE", "NUMERIC", "METRIC", "MEASURE")):
                _var_words(f.statement)
            _var_words(f.statement)  # also scan for explicit "<var> = <number>" patterns
        # 2) problem/conditions messages
        _var_words(getattr(state.problem, "description", ""))
        for c in getattr(state, "conditions", []):
            _var_words(c.message)

        # deterministic GCLV membership predicate (ACFL ec 4.17) over each numeric variable
        predictions: List[CandidatePrediction] = []
        for v in sorted(var_names)[:6]:
            ast = {
                "operator": "GCLV",
                "input": {"operator": "VARIABLE", "name": v},
                "alpha": 1.0,
                "gamma": 0.5,
                "m": 0.5,
                "authority_reference": "Tesis Carlos Llorente Eq 4.17",
            }
            predictions.append(CandidatePrediction(
                target=v, predicted_value=None, horizon="12 months",
                scenarios=[], uncertainty={}, candidate_predicates=[ast], method="ACFL_DETERMINISTIC",
            ))

        return PredictorProposal(
            candidate_predictions=predictions,
            limitations=["Deterministic ACFL math engine (no LLM): predictions depend only on numeric input data."],
        )

    def _deterministic_sufficiency(self, problem, task, knowledge) -> InformationSufficiencyProposal:
        """LS94 stall-fix — deterministic (NO LLM) information-sufficiency check for the
        ACFL/GCLV predictor. The Predictor is ACFL_DETERMINISTIC; it must NOT depend on a
        slow/nondeterministic LLM call (that left the step RUNNING / stuck). Rule: if there is
        any numeric value in the findings or the problem objective, the predictor can attempt a
        GCLV evaluation; otherwise it honestly reports NOT_EVALUATED (can_continue=True, so the
        step completes instead of stalling)."""
        texts = [getattr(f, "statement", "") for f in getattr(knowledge, "findings", [])] + \
                [getattr(problem, "objective", "")] + \
                [getattr(problem, "context", "") if hasattr(problem, "context") else ""]
        has_numeric = any(re.search(r"\d", str(t)) for t in texts if t)
        if has_numeric:
            return InformationSufficiencyProposal(sufficient=True, can_continue=True)
        return InformationSufficiencyProposal(
            sufficient=False,
            missing_information=[MissingInformationItem(
                name="numeric_historical_data",
                reason="No numeric/historical values available for ACFL/GCLV evaluation.",
                required_for="mathematical prediction",
            )],
            can_continue=True,   # NOT blocking: proceed, predictions will be NOT_EVALUATED
        )

    def execute(self, state: CanonicalWorkState, step: ExecutionStep) -> CanonicalWorkState:
        # 1. Relevance Gate
        if step.target != "EM Predictor" and "EM Predictor" not in step.target and step.capability_id not in ["predict", "forecast", "predict_outcome", "analyze_dataset"]:
            state.status = "GAP"
            state.waiting_reason = f"EM Predictor invoked for non-predictive task: {step.target}"
            return state

        # Extract the CognitiveTask from the ProblemModel
        task = None
        if state.problem and state.problem.structured_problem:
            for t in state.problem.structured_problem.task_network.tasks:
                if t.task_id == step.step_id:
                    task = t
                    break
        
        if not task:
            state.status = "GAP"
            state.waiting_reason = "Predictive cognitive task not found in TaskNetwork."
            return state

        # 2. Knowledge Dependency Gate (Gate 11)
        validated_findings = [f for f in state.knowledge.findings if f.status == "VALIDATED"]
        
        # Information Sufficiency Gate (LS60: NOT blocking — record + proceed)
        # LS94 stall-fix: deterministic check (NO LLM) so the ACFL predictor never stalls on a
        # slow/nondeterministic deepseek call (that left the step RUNNING / "stuck").
        sufficiency = self._deterministic_sufficiency(state.problem, task, state.knowledge)
        if not sufficiency.sufficient:
            from .canonical_state import HumanInteractionRequest, StateCondition as _SC
            # LS94/ask-once guard: ask for this missing data at most ONCE. Do NOT re-append a
            # MISSING_INFORMATION request if one for the same required info already exists
            # (pending OR answered), and do NOT re-ask once the user has already supplied data
            # (human_contributions present) — otherwise the pipeline re-asks forever on resume.
            mi = [mi.name for mi in sufficiency.missing_information]
            reqs = [r for r in (getattr(state, "human_requests", None) or [])]
            already_for_same = any(
                getattr(r, "type", None) == "MISSING_INFORMATION"
                and set(getattr(r, "required_information", []) or []) & set(mi)
                for r in reqs
            )
            already_answered = any(
                getattr(r, "type", None) == "MISSING_INFORMATION"
                and getattr(r, "status", None) in ("ANSWERED", "COMPLETED")
                for r in reqs
            )
            user_provided = bool(getattr(state, "human_contributions", None))
            if not (already_for_same or already_answered or user_provided):
                req = HumanInteractionRequest(
                    type="MISSING_INFORMATION",
                    question="Optional: provide the missing data required for mathematical prediction, or continue and the result will be marked NOT_EVALUATED.",
                    reason="Optional variables to reduce prediction uncertainty.",
                    required_information=mi,
                    blocking=False
                )
                state.human_requests.append(req)
            state.conditions.append(_SC(
                status="INFORMATIONAL",
                reason_code="INSUFFICIENT_DATA",
                message="Predictor has insufficient data; predictions will be marked NOT_EVALUATED."
            ))
            # Legacy field for tests
            state.information_request = sufficiency.model_dump()

        if state.knowledge.contradictions:
            state.status = "BLOCKED"
            state.waiting_reason = "Contradictory descriptive knowledge blocks prediction. Resolve contradiction first."
            return state

        # 3. Target / Horizon Validation
        if "decision" in task.description.lower() or "recommend" in task.description.lower() or "should" in task.description.lower():
            state.status = "GAP"
            state.waiting_reason = "Task is prescriptive, not predictive. Route to Prescriptor."
            return state

        # 4. Cognitive Engine Proposal — EM Predictor is a DETERMINISTIC Python/math process
        # (no LLM). It builds candidate predictions from numeric knowledge via the ACFL engine.
        import time as _time, uuid as _uuid
        t0 = _time.time()
        try:
            proposal: PredictorProposal = self._deterministic_propose_predictions(state, task)
            record_runtime_call(
                state, em="EM Predictor", capability_id=getattr(task, "capability_id", "propose_predictions"),
                call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model="ACFL_DETERMINISTIC",
                output_schema="PredictorProposal", latency_ms=(_time.time() - t0) * 1000,
                context_id=state.work.work_id if state.work else "", status="COMPLETED",
            )
        except Exception as e:
            record_runtime_call(
                state, em="EM Predictor", capability_id=getattr(task, "capability_id", "propose_predictions"),
                call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model="ACFL_DETERMINISTIC",
                output_schema="PredictorProposal", latency_ms=(_time.time() - t0) * 1000,
                context_id=state.work.work_id if state.work else "", status="FAILED",
            )
            state.status = "ERROR"
            state.waiting_reason = f"Deterministic predictor failure: {str(e)}"
            return state

        if not proposal.candidate_predictions:
            state.predictive_knowledge.status = "FROZEN"
            step.status = "COMPLETED"
            step.outputs["predictive_knowledge_status"] = "FROZEN"
            return state

        # 5. Mathematical Execution & Provenance
        T0 = "2026-01-01T00:00:00" # In a real system, this is a datetime, but for R4.1 we just ensure temporal logic holds.
        
        # Prepare inputs from KnowledgeState (simplified for R4.1 simulation)
        # Normally this maps historical evidence records into numerical dictionaries
        # Since we don't have a real time-series DB, we'll extract directly from step inputs or mock
        historical_records = step.inputs.get("historical_data", [])
        
        for candidate in proposal.candidate_predictions:
            # Gate 12: We IGNORE candidate.predicted_value from LLM.
            # Gate 14: Temporal Leakage check
            for rec in historical_records:
                if str(rec.get("timestamp", "")) > T0:
                    state.status = "FAILED"
                    state.waiting_reason = "TEMPORAL_LEAKAGE: Input data timestamp exceeds T0"
                    return state
            
            # Select best predicate
            best_mse = float('inf')
            best_predicate_obj = None
            best_pred_value = None
            best_scenarios = []

            if not candidate.candidate_predicates:
                # F-5 soft-lock fix: a candidate without a mathematical predicate (LLM could not propose
                # an IR AST, or there is no numeric data to evaluate) must NOT hard-pause the work as
                # WAITING_FOR_HUMAN_INPUT (that left the pipeline paused with no decision point / blocking
                # request). Skip this candidate — the aggregate is left NOT_EVALUATED and the step completes.
                continue

            from pydantic import TypeAdapter
            ast_adapter = TypeAdapter(AnyMathematicalExpression)

            # Evaluate each predicate (Gate 15)
            for raw_predicate in candidate.candidate_predicates:
                try:
                    # Validate Mathematical IR using TypeAdapter for Union
                    ast = ast_adapter.validate_python(raw_predicate)
                except Exception as e:
                    state.status = "FAILED"
                    state.waiting_reason = f"INVALID_PREDICATE: {str(e)}"
                    return state

                # Calculate MSE (Gate 13)
                actuals = []
                predicteds = []
                current_inputs = {}

                # We need at least one record to evaluate current state.
                if historical_records:
                    for rec in historical_records:
                        target_val = rec.get(candidate.target)
                        if target_val is not None:
                            try:
                                pred = self.engine.evaluate_expression(ast, rec)
                                predicteds.append(pred)
                                actuals.append(target_val)
                            except Exception as e:
                                pass # Skip bad records
                    
                    # Compute MSE
                    if actuals and predicteds:
                        mse = compute_mse(actuals, predicteds)
                    else:
                        mse = float('inf')
                        
                    current_inputs = historical_records[-1] # The most recent one for current prediction
                else:
                    mse = float('inf')
                    current_inputs = step.inputs.get("current_inputs", {})

                # Predict current value (LS60: skip ACFL evaluation when there is no numeric history,
                # so a consult without data proceeds and is marked NOT_EVALUATED instead of failing).
                if historical_records:
                    try:
                        current_pred = self.engine.evaluate_expression(ast, current_inputs)
                    except Exception as e:
                        state.status = "FAILED"
                        state.waiting_reason = f"UNSUPPORTED_MATHEMATICAL_OPERATOR: {str(e)}"
                        return state
                else:
                    current_pred = None

                # Update best predicate
                if mse < best_mse or (best_predicate_obj is None):
                    best_mse = mse
                    best_pred_value = current_pred
                    
                    pred_id = f"PRED_AST_{uuid.uuid4().hex[:8].upper()}"
                    best_predicate_obj = PredictivePredicate(
                        predicate_id=pred_id,
                        target=candidate.target,
                        logical_structure=ast,
                        mse=mse if mse != float('inf') else None,
                        status="VALIDATED",
                        provenance=["ACFL_ENGINE_V5.1", ast.authority_reference]
                    )

                    # Gate 16 - Scenarios
                    best_scenarios = []
                    for idx, s in enumerate(candidate.scenarios):
                        perturbed_inputs = dict(current_inputs)
                        perturbed_inputs.update(s.get("perturbed_variables", {}))
                        try:
                            scenario_pred = self.engine.evaluate_expression(ast, perturbed_inputs)
                            best_scenarios.append(PredictionScenario(
                                scenario_id=f"SCENARIO-{idx}",
                                name=s.get("name", f"Scenario {idx}"),
                                assumptions=s.get("assumptions", []),
                                perturbed_variables=s.get("perturbed_variables", {})
                            ))
                            # Add the result directly to the model conceptually or as metadata
                            best_scenarios[-1].provenance.append(f"Predicted_Value:{scenario_pred}")
                        except:
                            pass # If scenario fails, ignore it

            # Add to state
            state.predictive_knowledge.predicates.append(best_predicate_obj)
            
            # Gate 17 - Uncertainty MUST NOT BE HALLUCINATED
            uncertainty = PredictiveUncertainty(
                status="NOT_AVAILABLE",
                limitations=["No authoritative formula for ACFL uncertainty derivation"]
            )

            # Gate 20 - Reproducibility
            signature = self._generate_signature(
                state.knowledge.version, 
                best_predicate_obj.logical_structure.model_dump(), 
                current_inputs
            )

            pred_id = f"PRED-{uuid.uuid4().hex[:8].upper()}"
            # LS79.3 — linking: the prediction references the REAL findings (descriptive knowledge)
            # that informed it, so the chain Finding -> Prediction is traceable.
            pred_evidence_refs = [f.finding_id for f in state.knowledge.findings if getattr(f, "status", "") == "VALIDATED"] \
                or [f.finding_id for f in state.knowledge.findings]
            finding = PredictionKnowledge(
                prediction_id=pred_id,
                target_variable=candidate.target,
                predicted_value=best_pred_value, # computed, not LLM
                uncertainty=uncertainty,
                model_type="ACFL_ENGINE",
                model_definition=f"MSE={best_mse if best_mse != float('inf') else 'n/a'}",
                computation_trace=[
                    f"Task[{task.task_id}]",
                    f"Signature[{signature}]",
                    f"KnowledgeVersion[{state.knowledge.version}]"
                ],
                validation_status="VALIDATED" if best_mse != float('inf') else "NOT_EVALUATED",
                evidence_refs=pred_evidence_refs,
                predictor_variables=[candidate.target],
                input_requirements={candidate.target: "required input variable"},
                provenance=[
                    f"Task[{task.task_id}]",
                    f"Predicate[{best_predicate_obj.predicate_id}]",
                    f"Signature[{signature}]",
                    f"KnowledgeVersion[{state.knowledge.version}]"
                ]
            )

            if not finding.target_variable or finding.target_variable == "generic_target" and getattr(task, "description", "") == "Evaluate what we should recommend":
                # F-5 soft-lock fix: an undefined/generic target must NOT hard-pause the work as
                # WAITING_FOR_HUMAN_INPUT (that left the pipeline paused with no decision point / blocking
                # request). Keep the candidate as NOT_EVALUATED (honest) and let the step complete.
                finding.validation_status = "NOT_EVALUATED"

            state.predictive_knowledge.predictions.append(finding)

        state.predictive_knowledge.status = "FROZEN"
        step.status = "COMPLETED"
        step.outputs["predictive_knowledge_status"] = "FROZEN"
        return state
