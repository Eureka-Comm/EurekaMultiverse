from typing import Optional
from .canonical_state import CanonicalWorkState, ExecutionStep, WorkResult, StateCondition
from .acfl_engine import ACFLEngine
from .analytics_engine import ExplanatoryAnalyticsEngine
from .story_engine import StoryEngine
from .artifact_engine import ArtifactEngine
from .descriptor import EMDescriptor
from .predictor import EMPredictor
from .cognitive_engine import TestDoubleCognitiveEngine, record_runtime_call
from .human_input_sufficiency import MAX_HUMAN_INFORMATION_ATTEMPTS, count_information_attempts
from .effect_policy import EffectBoundary, DryRunContext, ExecutionMode, PolicyError, default_boundary
import datetime
import logging
import time as _time
import uuid as _uuid

logger = logging.getLogger(__name__)

class EvidenceReadinessResolver:
    @staticmethod
    def resolve(canonical: CanonicalWorkState, step: ExecutionStep) -> dict:
        if not canonical.evidence:
            # LS60: evidence is OPTIONAL — proceed using the user intent/problem context.
            return {"status": "READY"}
        
        statuses = [e.extraction_status for e in canonical.evidence]
        
        if any(s == "FAILED" for s in statuses):
            failed = next(e for e in canonical.evidence if e.extraction_status == "FAILED")
            return {"status": "FAILED", "reason_code": failed.extraction_reason_code or "SYSTEM_ERROR", "message": failed.extraction_error or "Evidence parsing failed."}
            
        if any(s == "GAP" for s in statuses):
            gapped = next(e for e in canonical.evidence if e.extraction_status == "GAP")
            return {"status": "GAP", "reason_code": gapped.extraction_reason_code or "UNSUPPORTED_EVIDENCE_FORMAT", "message": gapped.extraction_error or "Evidence unsupported."}
            
        if any(s in ["NOT_STARTED", "PARSING"] for s in statuses):
            waiting_ids = [e.evidence_id for e in canonical.evidence if e.extraction_status in ["NOT_STARTED", "PARSING"]]
            return {"status": "WAITING_FOR_EVIDENCE", "waiting_ids": waiting_ids, "message": f"Waiting for evidence parsing: {', '.join(waiting_ids)}"}
            
        if any(s == "PARTIAL" for s in statuses):
            return {"status": "PARTIAL"}
            
        return {"status": "READY"}

_execution_locks = set()

# B1/B2 resilience: a transient error (LLM / network / timeout) during a single
# capability invocation must NOT permanently fail the whole work. We keep a
# bounded per-step retry budget and only escalate to FAILED once it is exhausted
# for a step, so a genuinely transient failure no longer clobbers a healthy run.
_step_retries: dict[str, int] = {}
MAX_STEP_RETRIES = 3

class WorkRuntime:
    """
    Manages the lifecycle of a CanonicalWorkState execution.
    Executes the ExecutionPlan and ensures strict state transitions.
    """
    def __init__(self, cognitive_engine=None):
        self.acfl_engine = ACFLEngine()
        self.analytics_engine = ExplanatoryAnalyticsEngine()
        self.story_engine = StoryEngine()
        self.artifact_engine = ArtifactEngine()
        # LS-SCN-03: single structural gate below agent/LLM intent & above mutable side effects.
        # NORMAL mode is permissive (unchanged); DRY_RUN is strict fail-closed. `_dry_run` is set
        # per-advance by any future controlled context; default False preserves current behavior.
        self._effect_boundary: EffectBoundary = default_boundary()
        self._dry_run: bool = False
        
        engine = cognitive_engine or TestDoubleCognitiveEngine()
        self.descriptor = EMDescriptor(cognitive_engine=engine)
        self.predictor = EMPredictor(cognitive_engine=engine)
        
        from .actioner import EMActioner
        from .installer import EMInstaller
        from .publisher import EMPublisher
        from .governed_execution_adapter import GovernedExecutionAdapter
        from .prescriptor import EMPrescriptor
        self.actioner = EMActioner(cognitive_engine=engine)
        # PRODUCTION executor: governed, observable, durable (NOT the Controlled test-double). The
        # mode is derived from this runtime's dry-run flag; a real work execution uses REAL_EXECUTION.
        self.installer = EMInstaller(GovernedExecutionAdapter(
            boundary=self._effect_boundary,
            mode=ExecutionMode.DRY_RUN if self._dry_run else ExecutionMode.REAL_EXECUTION))
        self.publisher = EMPublisher(cognitive_engine=engine, boundary=self._effect_boundary,
                                     mode=ExecutionMode.DRY_RUN if self._dry_run else ExecutionMode.REAL_EXECUTION)
        self.prescriptor = EMPrescriptor(cognitive_engine=engine)


    def advance(self, canonical: CanonicalWorkState) -> CanonicalWorkState:
        # Sync the governed executor's Q4 mode with this runtime's dry-run flag: DRY_RUN blocks the
        # real effect, REAL_EXECUTION allows the governed, observable artifact write.
        try:
            self.installer.adapter.mode = ExecutionMode.DRY_RUN if self._dry_run else ExecutionMode.REAL_EXECUTION
            self.publisher.mode = ExecutionMode.DRY_RUN if self._dry_run else ExecutionMode.REAL_EXECUTION
        except AttributeError:
            pass  # a (test) adapter/publisher with no `mode` attribute simply runs as-is

        for s in canonical.execution_plan.steps:
            pass
        result_required = any(step.produces_result for step in canonical.execution_plan.steps)
        if result_required and (not canonical.result or canonical.result.status != "AVAILABLE"):
            if canonical.status == "COMPLETED":
                canonical.status = "GAP"
                canonical.conditions.append(StateCondition(
                    status="GAP",
                    reason_code="RESULT_UNAVAILABLE",
                    message="A result-producing capability was required but the result is unavailable."
                ))
                
        if canonical.status == "WAITING_FOR_EVIDENCE":
            if not canonical.evidence:
                canonical.status = "GAP"
                canonical.conditions.append(StateCondition(
                    status="GAP",
                    reason_code="EVIDENCE_MISSING",
                    message="Required evidence is missing."
                ))
                return canonical
            else:
                canonical.status = "READY"

        if canonical.status in ["FAILED", "COMPLETED", "BLOCKED", "GAP"]:
            return canonical

        if canonical.status == "READY":
            canonical.status = "RUNNING"
            
        has_gaps = False
        all_completed = True
        
        # Evaluate dependencies and transition PENDING to READY
        for step in canonical.execution_plan.steps:
            if step.status == "PENDING":
                deps_met = True
                for dep_id in step.dependencies:
                    dep_step = next((s for s in canonical.execution_plan.steps if s.step_id == dep_id), None)
                    if not dep_step or dep_step.status != "COMPLETED":
                        deps_met = False
                        break
                if deps_met:
                    step.status = "READY"
                    
        
        # Execute exactly one step
        for step in canonical.execution_plan.steps:
            if step.status == "GAP":
                has_gaps = True
                all_completed = False
                break
            if step.status in ["BLOCKED", "FAILED"]:
                all_completed = False
                break
                
            if step.status == "COMPLETED":
                continue

            # If it's already RUNNING or WAITING_*, we are ready to execute it now
            if step.status in ["RUNNING", "READY", "WAITING_FOR_EVIDENCE", "WAITING_FOR_HUMAN_INPUT", "PARTIAL"]:
                if step.status == "WAITING_FOR_EVIDENCE" and EvidenceReadinessResolver.resolve(canonical, step)["status"] != "READY":
                    return canonical
                    
                if step.status == "WAITING_FOR_HUMAN_INPUT":
                    return canonical
                    
                lock_key = f"{canonical.work.work_id}_{step.step_id}"
                if lock_key in _execution_locks:
                    return canonical
                    
                if not step.started_at:
                    step.started_at = datetime.datetime.now().isoformat()
                # We found a step to execute!
                from .canonical_state import ExecutionEvent

                # If it's READY, mark it RUNNING and record event
                if step.status == "READY" or step.status == "PARTIAL":
                    step.status = "RUNNING"
                    step.started_at = datetime.datetime.now().isoformat()
                    canonical.active_em = step.canonical_em
                    canonical.active_step_id = step.step_id
                    canonical.active_capability = step.capability_id

                    canonical.execution_events.append(ExecutionEvent(
                        timestamp=step.started_at,
                        step_id=step.step_id,
                        canonical_em=step.canonical_em or "UNKNOWN",
                        capability_id=step.capability_id,
                        event="STEP_RUNNING",
                        status="RUNNING",
                        message=f"Starting capability: {step.capability_id}"
                    ))
                    canonical.revision += 1
                    return canonical # Return so React can observe the RUNNING state

                # We are actually executing it now
                _execution_locks.add(lock_key)
                try:
                    self._execute_step(canonical, step)
                    
                    # Ensure execution_state is mirrored for UI
                    if step.status == "WAITING_FOR_EVIDENCE":
                        canonical.execution_phase = "WAITING_FOR_EVIDENCE"
                    else:
                        canonical.execution_phase = "RUNNING"
                        canonical.waiting_reason = ""   # schema is `str = ""`; None would fail reload
                        canonical.waiting_for_evidence_ids = []
                        
                    # Check if step execution caused a terminal/waiting state
                    if step.status not in ["GAP", "BLOCKED", "FAILED", "WAITING_FOR_EVIDENCE", "WAITING_FOR_HUMAN_INPUT"]:
                        # Completion Gate (LS52): a result-producing step must leave an AVAILABLE result.
                        # If it does not (e.g. the Publisher rejected/returned NOT_READY for a minimal
                        # plan, or a summary capability produced nothing), synthesize a truthful
                        # WorkResult from the canonical data so the work never ends GAP /
                        # "No actionable execution output".
                        if getattr(step, "produces_result", False) and (not canonical.result or canonical.result.status != "AVAILABLE"):
                            import uuid as _uuid
                            from .canonical_state import WorkResult as _WR
                            obj = canonical.problem.objective if (canonical.problem and canonical.problem.objective) else "N/D"
                            n_presc = len(canonical.prescriptive_knowledge.prescriptions) if canonical.prescriptive_knowledge else 0
                            n_answered = sum(1 for d in canonical.decision_points if d.status == "ANSWERED")
                            summary = (f"EUREKA completó el análisis ({step.canonical_em or step.capability_id}) y compiló un resultado "
                                       f"final desde el estado canónico. Objetivo: {obj}. Hallazgos validados: "
                                       f"{len(canonical.knowledge.findings)}. Prescripciones: {n_presc}. "
                                       f"Decisiones humanas: {n_answered}.")
                            # F-4 (no-sustitución): the runtime fallback must NOT present a fabricated
                            # result as an AVAILABLE analysis. Mark it PARTIAL with explicit limitations
                            # so it is transparent that no validated analysis was produced. Only fires
                            # when a produces_result step leaves no available result; a real Publisher
                            # still yields an AVAILABLE result and is unaffected.
                            canonical.result = _WR(
                                result_id=f"WR-{_uuid.uuid4().hex[:6]}",
                                work_id=canonical.work.work_id,
                                summary=summary,
                                status="PARTIAL",
                                provenance=["Runtime compiled result (fallback)"],
                                limitations=[
                                    "Resultado compilado por el runtime como fallback: no se produjo un "
                                    "análisis validado. El paso productor de resultado no dejó un resultado "
                                    "disponible (no-sustitución)."
                                ]
                            )
                            step.status = "COMPLETED"
                            step.completed_at = datetime.datetime.now().isoformat()
                        else:
                            step.status = "COMPLETED"
                            step.completed_at = datetime.datetime.now().isoformat()
                        
                        canonical.execution_events.append(ExecutionEvent(
                            timestamp=step.completed_at if step.completed_at else datetime.datetime.now().isoformat(),
                            step_id=step.step_id,
                            canonical_em=step.canonical_em or "UNKNOWN",
                            capability_id=step.capability_id,
                            event=f"STEP_{step.status}",
                            status=step.status,
                            message=f"Capability {step.capability_id} yielded {step.status}",
                            provenance=step.provenance.copy()
                        ))
                    elif step.status == "WAITING_FOR_EVIDENCE":
                        # Do not change canonical.status to WAITING, keep it RUNNING, but update events
                        pass
                    else:
                        canonical.status = step.status
                        canonical.execution_events.append(ExecutionEvent(
                            timestamp=datetime.datetime.now().isoformat(),
                            step_id=step.step_id,
                            canonical_em=step.canonical_em or "UNKNOWN",
                            capability_id=step.capability_id,
                            event=f"STEP_{step.status}",
                            status=step.status,
                            message=f"Capability {step.capability_id} yielded {step.status}"
                        ))
                except Exception as e:
                    import traceback
                    print("RUNTIME ERROR IN CAPABILITY:", step.capability_id)
                    traceback.print_exc()
                    key = f"{canonical.work.work_id}_{step.step_id}"
                    retries = _step_retries.get(key, 0) + 1
                    _step_retries[key] = retries
                    # B1/B2 (bounded retry): believe the error is transient at first.
                    # Record it, keep the step retryable and the work RUNNING so the
                    # background loop retries it; only terminal-fail after MAX_STEP_RETRIES.
                    if retries < MAX_STEP_RETRIES:
                        canonical.conditions.append(StateCondition(
                            status="INFORMATIONAL",
                            reason_code="STEP_RETRY",
                            message=f"Transient error on {step.step_id} (attempt {retries}/{MAX_STEP_RETRIES}): {str(e)}",
                            target=step.capability_id,
                        ))
                        step.status = "READY"
                        canonical.status = "RUNNING"
                        canonical.execution_events.append(ExecutionEvent(
                            timestamp=datetime.datetime.now().isoformat(),
                            step_id=step.step_id,
                            canonical_em=step.canonical_em or "UNKNOWN",
                            capability_id=step.capability_id,
                            event="STEP_RETRY",
                            status="READY",
                            message=f"Retrying {step.capability_id} (attempt {retries}/{MAX_STEP_RETRIES}) after transient error: {str(e)}",
                        ))
                    else:
                        step.status = "FAILED"
                        canonical.status = "FAILED"
                        canonical.conditions.append(StateCondition(
                            status="FAILED",
                            reason_code="SYSTEM_ERROR",
                            message=f"Step {step.step_id} failed after {retries} attempts: {str(e)}",
                            target=step.capability_id,
                        ))
                        canonical.execution_events.append(ExecutionEvent(
                            timestamp=datetime.datetime.now().isoformat(),
                            step_id=step.step_id,
                            canonical_em=step.canonical_em or "UNKNOWN",
                            capability_id=step.capability_id,
                            event="STEP_FAILED",
                            status="FAILED",
                            message=str(e),
                        ))
                
                finally:
                    if lock_key in _execution_locks:
                        _execution_locks.remove(lock_key)
                    # Reset the transient-retry budget once a step commits to a non-retry
                    # state (a retry leaves the step as READY and must keep its budget).
                    if step.status != "READY":
                        _step_retries.pop(f"{canonical.work.work_id}_{step.step_id}", None)

                canonical.revision += 1
                return canonical # Execute one at a time
                
        # If we loop through and nothing executed
        # Evaluate final status
        if canonical.status == "FAILED":
            return canonical
            
        # If no executable steps were found, the pipeline is finished or stuck.
        # Check remaining non-completed statuses:
        has_failed = any(s.status == "FAILED" for s in canonical.execution_plan.steps)
        has_blocked = any(s.status == "BLOCKED" for s in canonical.execution_plan.steps)
        has_gaps = any(s.status == "GAP" for s in canonical.execution_plan.steps)
        has_waiting_evidence = any(s.status == "WAITING_FOR_EVIDENCE" for s in canonical.execution_plan.steps)
        has_waiting_human = any(s.status == "WAITING_FOR_HUMAN_INPUT" for s in canonical.execution_plan.steps)
        has_active = any(s.status in ["PENDING", "READY", "RUNNING", "PARTIAL"] for s in canonical.execution_plan.steps)
        
        if has_failed:
            canonical.status = "FAILED"
        elif has_blocked:
            canonical.status = "BLOCKED"
        elif has_gaps:
            canonical.status = "GAP"
        elif has_waiting_human:
            canonical.status = "WAITING_FOR_HUMAN_INPUT"
        elif has_active:
            canonical.status = "RUNNING"
        elif has_waiting_evidence:
            canonical.status = "RUNNING"
            canonical.execution_phase = "WAITING_FOR_EVIDENCE"
        else:
            canonical.status = "COMPLETED"
            canonical.execution_phase = "COMPLETED"
            
        # Compile Result if applicable
        if canonical.status in ["COMPLETED", "PARTIAL"]:
            self._compile_result(canonical)
            
            # Re-check invariant after compiling result
            if result_required and (not canonical.result or canonical.result.status != "AVAILABLE"):
                if canonical.status == "COMPLETED":
                    canonical.status = "GAP"
                    canonical.conditions.append(StateCondition(
                        status="GAP",
                        reason_code="RESULT_UNAVAILABLE",
                        message="A result-producing capability was required but the result is unavailable."
                    ))
            
        return canonical

    def _maybe_request_missing_data(self, canonical: CanonicalWorkState) -> bool:
        """LS94 — REQUEST MISSING DATA (HITL information gathering).

        After the EM Descriptor, when the operation is a natural-question / knowledge / open-research
        operation AND the evidence is genuinely INSUFFICIENT to answer substantively, the LLM proposes
        the SPECIFIC missing data (a CANDIDATE) and Python — never the LLM — decides that the request is
        BLOCKING and persists it as a real ``HumanInteractionRequest(type="INFORMATION", blocking=True,
        decision_required=False)``, then pauses the workflow on ``WAITING_FOR_HUMAN_INPUT``.

        Python-authority guards (so LS92 correct answers are preserved):
        - Selection/decision-selection questions ("elige entre estas opciones") are NOT touched — they
          keep the full 8-EM + HITL decision gate.
        - If the Descriptor grounded findings in REAL uploaded evidence, the question IS answerable —
          never ask.
        - The LLM candidate is only the CONTENT (what data is missing). Python decides blocking + persists.
        - If the LLM candidate says data_needed=False (self-answerable) or is incoherent, we never ask.

        Returns True when a blocking request was created.
        """
        prob = canonical.problem
        if prob is None:
            return False
        op_mode = getattr(prob, "operation_mode", "DECISION") or "DECISION"
        user_intent = (prob.intent or (canonical.work.user_intent if canonical.work else "")) or ""
        # 1. Selection / decision-selection intents are NOT the missing-data case — they keep the
        #    full 8-EM + HITL decision gate (LS92 HITL preserved).
        from .orchestrator import _DECISION_VERB_RE
        if _DECISION_VERB_RE.search(user_intent or ""):
            return False
        # 2. Scope: natural-question / knowledge / open-research operations. A KNOSWLEDGE_ANSWER or a
        #    still-open (undecided) DECISION question can lack the data to answer substantively.
        if op_mode not in ("KNOWLEDGE_ANSWER", "DECISION"):
            return False
        # 3. Do NOT ask again when the human has already provided SUFFICIENT information. The verdict
        #    belongs to Python (human_input_sufficiency), never to the LLM — and an INSUFFICIENT /
        #    PARTIAL response does NOT close the gate (the request is repeated with the missing items).
        _info_reqs = [hr for hr in (getattr(canonical, "human_requests", None) or [])
                      if getattr(hr, "type", "") == "INFORMATION"]
        _answered_reqs = [hr for hr in _info_reqs
                          if getattr(hr, "status", "") in ("ANSWERED", "COMPLETED")]
        _evaluated = [hr for hr in _answered_reqs
                      if (getattr(hr, "sufficiency_status", "NOT_EVALUATED") or "NOT_EVALUATED") != "NOT_EVALUATED"]
        if any((getattr(hr, "sufficiency_status", "") or "") == "SUFFICIENT" for hr in _answered_reqs):
            return False
        #    Legacy compatibility (works persisted BEFORE the sufficiency contract existed): a
        #    VALIDATED finding carrying the historical "HUMAN_INPUT" label still counts as provided.
        if not _evaluated and (
            any(
                getattr(f, "status", "") == "VALIDATED" and "HUMAN_INPUT" in (getattr(f, "evidence_refs", None) or [])
                for f in (list(getattr(canonical.knowledge, "findings", None) or []))
            ) or any(
                getattr(c, "type", "") == "INFORMATION"
                for c in (getattr(canonical, "human_contributions", None) or [])
            )
        ):
            return False
        # 3b. Anti-loop (bounded): when the governed request budget is spent we neither loop forever
        #     nor publish over missing information — the work stays BLOCKED with an explicit condition.
        if count_information_attempts(getattr(canonical, "human_requests", None)) >= MAX_HUMAN_INFORMATION_ATTEMPTS:
            if not any(c.reason_code == "HUMAN_INPUT_EXHAUSTED" for c in canonical.conditions):
                canonical.conditions.append(StateCondition(
                    status="WAITING_FOR_HUMAN_INPUT",
                    reason_code="HUMAN_INPUT_EXHAUSTED",
                    message=(f"Se agotaron los {MAX_HUMAN_INFORMATION_ATTEMPTS} intentos de solicitud de información y la "
                             f"respuesta recibida no fue suficiente: el trabajo permanece bloqueado y NO se publica una "
                             f"respuesta no fundamentada.")))
            return True
        # 4. Python-authority sufficiency guard: if the Descriptor grounded findings in REAL uploaded
        #    evidence (evidence_refs beyond the synthetic EVI-CONTEXT / HUMAN_INPUT), the question IS
        #    answerable from real data -> NEVER ask (preserves LS92 answers grounded in attached data).
        if any(
            getattr(f, "status", "") == "VALIDATED"
            and any(r for r in (getattr(f, "evidence_refs", None) or []) if r not in ("EVI-CONTEXT", "HUMAN_INPUT"))
            for f in (list(getattr(canonical.knowledge, "findings", None) or []))
        ):
            return False
        # 5. LLM proposes WHAT is missing (candidate only). Python validates + persists. The LLM's
        #    data_needed is the content signal: it distinguishes self-answerable questions (False)
        #    from questions that genuinely need the user's specific data (True). Python never lets the
        #    LLM decide authority — it only sources the content; Python decides blocking + persists.
        proposal = None
        _engine = self._cognitive_engine_for(canonical)
        _probe_t0 = _time.time()
        _probe_call_id = f"CALL-{_uuid.uuid4().hex[:8]}"
        _probe_model = getattr(_engine, "model", None) or type(_engine).__name__
        _probe_ctx = canonical.work.work_id if canonical.work else ""

        def _record_probe(status: str) -> None:
            # PROVENANCE: the probe REALLY happened (it is not retrospective), so it is recorded —
            # and a degraded probe is recorded as degraded, never as a clean "no data needed".
            record_runtime_call(canonical, em="EM Descriptor", capability_id="propose_missing_data",
                                call_id=_probe_call_id, model=_probe_model,
                                output_schema="MissingDataProposal",
                                latency_ms=(_time.time() - _probe_t0) * 1000,
                                context_id=_probe_ctx, status=status)

        try:
            proposal = _engine.propose_missing_data(
                prob, [getattr(f, "statement", "") for f in (list(getattr(canonical.knowledge, "findings", None) or []))]
            )
        except Exception as e:  # fail CLOSED: an unreachable/degraded LLM must not fabricate a request
            _record_probe("FAILED")
            logger.warning("LS94 propose_missing_data unavailable (%s); not asking (normal publish).", e)
            if not any(c.reason_code == "MISSING_DATA_PROBE_FAILED" for c in canonical.conditions):
                canonical.conditions.append(StateCondition(
                    status="INFORMATIONAL", reason_code="MISSING_DATA_PROBE_FAILED",
                    message=("La sonda de suficiencia (LLM) no estuvo disponible: no se creó una solicitud de "
                             "información. El hecho queda registrado (no silencioso).")))
            return False
        _probe_status = (getattr(proposal, "evaluation_status", "OK") or "OK")
        _record_probe("COMPLETED" if _probe_status == "OK" else _probe_status)
        if _probe_status != "OK":
            if not any(c.reason_code == "MISSING_DATA_PROBE_DEGRADED" for c in canonical.conditions):
                canonical.conditions.append(StateCondition(
                    status="INFORMATIONAL", reason_code="MISSING_DATA_PROBE_DEGRADED",
                    message=(f"Sonda de suficiencia degradada ({_probe_status}, attempts="
                             f"{getattr(proposal, 'attempts', 1)}): no se creó solicitud de información; "
                             f"la respuesta se publica declarando esta limitación.")))
        if proposal is None or not getattr(proposal, "data_needed", False):
            return False
        required = [r for r in (getattr(proposal, "required_information", None) or []) if str(r).strip()]
        question = (getattr(proposal, "question", "") or "").strip()
        if not required or not question:
            return False
        from .canonical_state import HumanInteractionRequest
        canonical.human_requests.append(HumanInteractionRequest(
            type="INFORMATION",
            question=question,
            # CANONICAL ASSOCIATION: the request knows the Work it belongs to (stamped at creation).
            work_id=(canonical.work.work_id if canonical.work else ""),
            reason=(getattr(proposal, "reason", None) or (
                "LS94: el Descriptor no pudo fundamentar hallazgos (evidencia insuficiente); se solicita "
                "la información específica para realizar un análisis fundamentado. Solicitado por Python, "
                "no generado por el LLM como autoridad.")),
            required_information=required,
            decision_required=False,
            blocking=True,
        ))
        canonical.conditions.append(StateCondition(
            status="WAITING_FOR_HUMAN_INPUT",
            reason_code="MISSING_DATA_REQUESTED",
            message="LS94: datos insuficientes para responder de forma fundamentada; se solicita la "
                    "información específica al usuario. Requerido: " + "; ".join(required),
        ))
        # Pause the workflow: mark the next executable step (the Publisher for a KNOWLEDGE_ANSWER plan)
        # as WAITING_FOR_HUMAN_INPUT so the run halts BEFORE publishing a thin/unsupported answer.
        self._set_next_step_waiting(canonical)
        return True

    def _cognitive_engine_for(self, canonical: CanonicalWorkState):
        """Return the cognitive engine used by the Descriptor for this run (for the missing-data probe)."""
        return getattr(self.descriptor, "cognitive_engine", None) or TestDoubleCognitiveEngine()

    def _set_next_step_waiting(self, canonical: CanonicalWorkState) -> bool:
        """Mark the next executable (PENDING/READY) step after the currently-running step as
        WAITING_FOR_HUMAN_INPUT so the workflow halts (and resumes on human data). Prefers a
        produces_result step (the Publisher) so the resumed run publishes the grounded answer.

        Returns True when a step was put into the waiting state.
        """
        steps = list(canonical.execution_plan.steps or [])
        if not steps:
            return False
        # Prefer the produces_result (Publisher) step so a resumed run publishes the grounded
        # answer. Fall back to the first PENDING/READY step after the running one, then any PENDING.
        target = next((s for s in steps if getattr(s, "produces_result", False) and s.status in ("PENDING", "READY")), None)
        if target is None:
            current = next((s for s in steps if s.status == "RUNNING"), None)
            idx = next((i for i, s in enumerate(steps) if current and s.step_id == current.step_id), -1)
            after = steps[idx + 1:] if idx >= 0 else steps
            target = next((s for s in after if s.status in ("PENDING", "READY")), None)
        if target is None:
            target = next((s for s in steps if s.status == "PENDING"), None)
        if target is None:
            return False
        target.status = "WAITING_FOR_HUMAN_INPUT"
        target.waiting_reason = "LS94: waiting for the specific information requested from the user."
        return True

    def _execute_step(self, canonical: CanonicalWorkState, step: ExecutionStep):
        # LS-SCN-03: enforce the effect boundary BEFORE any capability handler can run.
        # In DRY_RUN a MUTATE/UNKNOWN capability is blocked (fail-closed) and never reaches the
        # real handler. In NORMAL mode (default) behavior is unchanged.
        if self._dry_run:
            try:
                self._effect_boundary.enforce(DryRunContext(
                    capability_id=step.capability_id,
                    target=step.target or "",
                    mode=ExecutionMode.DRY_RUN,
                    execution_level=0,
                    required_execution_level=0,
                ))
            except PolicyError as err:
                step.status = "BLOCKED"
                canonical.conditions.append(StateCondition(
                    status="BLOCKED",
                    reason_code=err.reason_code,
                    message=f"Dry-run blocked: {err.message}",
                    target=step.capability_id,
                ))
                return
        # Determine execution logic
        if step.capability_id in ["adjust_acfl_weights"]:
            # Route to ACFL Engine
            self.acfl_engine.execute(canonical, step)
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> ACFLEngine")
            

        elif step.capability_id == "frozen_knowledge.detect_delta":
            hc = canonical.historical_context
            frozen = hc.model_dump() if hc else {}
            prob = canonical.problem.model_dump() if canonical.problem else {}
            
            from .cognitive_engine import DeepSeekAdapter
            engine = DeepSeekAdapter()
            res = engine.detect_delta(frozen, prob)
            
            from .canonical_state import DeltaAssessment, DeltaItem
            items = []
            for item in res.items:
                items.append(DeltaItem(**item))
            
            da = DeltaAssessment(
                status="EVALUATED",
                frozen_solution_id=hc.frozen_solution_id if hc else "UNKNOWN",
                frozen_version=hc.version if hc else "UNKNOWN",
                current_problem_id="PROBLEM_002",
                items=items,
                confidence=res.confidence
            )
            canonical.historical_context.delta_assessment = da
            step.status = "COMPLETED"

        elif step.capability_id == "frozen_knowledge.mathematical_revalidation":
            hc = canonical.historical_context
            frozen = hc.model_dump() if hc else {}
            
            from .server import evidence_store
            ev_content = ""
            for ev in canonical.evidence:
                c = evidence_store.get(ev.evidence_id, {}).get("extracted_evidence", {}).get("content", "No content")
                ev_content += f"Evidence {ev.filename}: {c}\n"
            
            from .cognitive_engine import DeepSeekAdapter
            engine = DeepSeekAdapter()
            res = engine.mathematical_revalidation(frozen, ev_content)
            
            from .canonical_state import MathematicalRevalidationAssessment, MathematicalRevalidationResult
            
            val_preds = [MathematicalRevalidationResult(**x) for x in res.validated_predictions]
            inval_preds = [MathematicalRevalidationResult(**x) for x in res.invalidated_predictions]
            insuf_preds = [MathematicalRevalidationResult(**x) for x in res.insufficient_data_predictions]
            
            mra = MathematicalRevalidationAssessment(
                status=res.status,
                validated_predictions=val_preds,
                invalidated_predictions=inval_preds,
                insufficient_data_predictions=insuf_preds,
                required_data=res.required_data
            )
            canonical.historical_context.mathematical_revalidation = mra
            
            if res.status == "MATHEMATICAL_CAPABILITY_NOT_YET_EXECUTABLE":
                canonical.conditions.append(StateCondition(
                    status="FAILED",
                    reason_code="MATHEMATICAL_CAPABILITY_NOT_YET_EXECUTABLE",
                    message=f"Frozen solution lacks mathematical predictive contract: {res.required_data}"
                ))
                step.status = "FAILED"
                canonical.status = "FAILED"
            else:
                step.status = "COMPLETED"

        elif step.capability_id == "frozen_knowledge.cognitive_reevaluation":
            hc = canonical.historical_context
            frozen = hc.model_dump() if hc else {}
            da = hc.delta_assessment.model_dump() if hc and hc.delta_assessment else {}
            mra = hc.mathematical_revalidation.model_dump() if hc and hc.mathematical_revalidation else {}
              # print("MRA BEFORE COGNITIVE REEVALUATION:", mra)
            
            from .cognitive_engine import DeepSeekAdapter
            engine = DeepSeekAdapter()
            res = engine.cognitive_reevaluation(frozen, da, mra)
            
            from .canonical_state import CognitiveReevaluationAssessment
            
            cra = CognitiveReevaluationAssessment(
                status=res.status,
                knowledge_status=res.knowledge_status,
                prediction_status=res.prediction_status,
                prescription_status=res.prescription_status,
                decision_status=res.decision_status,
                rationale=res.rationale,
                previous_prescription_id=res.previous_prescription_id,
                previous_prediction_ids=res.previous_prediction_ids,
                current_prediction_ids=res.current_prediction_ids,
                delta_ids=res.delta_ids,
                revalidation_status=res.revalidation_status,
                new_alternatives=res.new_alternatives,
                uncertainty=res.uncertainty,
                validity_conditions=res.validity_conditions,
                human_decision_required=res.human_decision_required,
                required_data=[d if isinstance(d, dict) else d.model_dump() if hasattr(d, "model_dump") else d for d in res.required_data],
                invalidated_reason=res.invalidated_reason,
                invalidated_predictions=res.invalidated_predictions,
                dependent_prescriptions=res.dependent_prescriptions
            )
            canonical.historical_context.cognitive_reevaluation = cra
            
            print(f"CRA NEW ALTS: {cra.new_alternatives}, P_STATUS: {res.prescription_status}, D_STATUS: {res.decision_status}")
            print(f"FROZEN PRESC: {frozen.get('prescriptive_knowledge')}")
            if not cra.new_alternatives and res.prescription_status not in ["MISSING_PREDICTIVE_KNOWLEDGE", "INSUFFICIENT_DATA", "PRESCRIPTION_INVALIDATED"]:
                if frozen and frozen.get("prescriptive_knowledge") and frozen["prescriptive_knowledge"].get("prescriptions"):
                    cra.new_alternatives = frozen["prescriptive_knowledge"]["prescriptions"][-1].get("alternatives", [])
            if cra.new_alternatives:
                from .prescription_model import ValidatedPrescription, PrescriptionAlternative, DecisionRule
                import uuid
                alts = [PrescriptionAlternative(**a) if isinstance(a, dict) else a for a in cra.new_alternatives]
                presc = ValidatedPrescription(
                    prescription_id=f"PRESC-{uuid.uuid4()}",
                    objective="Re-evaluated Objective",
                    alternatives=alts,
                    applicable_criteria=[],
                    constraints=[],
                    decision_rule=DecisionRule(status="DOCUMENTED", rule_type="SYSTEM", authority="SYSTEM"),
                    supporting_predictions=cra.current_prediction_ids,
                    supporting_knowledge=[],
                    rationale=cra.rationale,
                    authority="SYSTEM",
                    provenance=["Cognitive Re-evaluation"],
                    validation_status="HUMAN_DECISION_REQUIRED"
                )
                if not canonical.prescriptive_knowledge:
                    from .prescription_model import PrescriptiveKnowledgeState
                    canonical.prescriptive_knowledge = PrescriptiveKnowledgeState()
                canonical.prescriptive_knowledge.prescriptions.append(presc)
                
            if res.decision_status == "HUMAN_REVIEW_REQUIRED":
                canonical.conditions.append(StateCondition(
                    status="WAITING_FOR_HUMAN_INPUT",
                    reason_code="HUMAN_DECISION_REQUIRED",
                    message="Cognitive re-evaluation complete. Human decision required."
                ))
                step.status = "WAITING_FOR_HUMAN_INPUT"
                canonical.status = "WAITING_FOR_HUMAN_INPUT"
            elif res.decision_status == "WAITING_FOR_HUMAN_INPUT":
                canonical.conditions.append(StateCondition(
                    status="WAITING_FOR_HUMAN_INPUT",
                    reason_code="INSUFFICIENT_DATA",
                    message="Cognitive re-evaluation requires more data."
                ))
                step.status = "WAITING_FOR_HUMAN_INPUT"
                canonical.status = "WAITING_FOR_HUMAN_INPUT"
            else:
                step.status = "COMPLETED"

        elif step.capability_id == "frozen_knowledge.action_plan_generation":

            if not canonical.human_decision:
                canonical.conditions.append(StateCondition(
                    status="WAITING_FOR_HUMAN_INPUT",
                    reason_code="HUMAN_DECISION_REQUIRED",
                    message="Human decision required before Action Plan can be generated."
                ))
                step.status = "WAITING_FOR_HUMAN_INPUT"
                canonical.status = "WAITING_FOR_HUMAN_INPUT"
            elif canonical.human_decision.decision_type == "REJECT_ALL":
                canonical.conditions.append(StateCondition(
                    status="WAITING_FOR_HUMAN_INPUT",
                    reason_code="HUMAN_REVIEW_REQUIRED",
                    message="Human rejected all alternatives."
                ))
                step.status = "WAITING_FOR_HUMAN_INPUT"
                canonical.status = "WAITING_FOR_HUMAN_INPUT"
            else:
                cra = canonical.historical_context.cognitive_reevaluation if canonical.historical_context else None
                if cra and cra.prescription_status == "PRESCRIPTION_INVALIDATED":
                    canonical.conditions.append(StateCondition(
                        status="WAITING_FOR_HUMAN_INPUT",
                        reason_code="INVALIDATED_PRESCRIPTION",
                        message="Cannot generate action plan for invalidated prescription."
                    ))
                    step.status = "WAITING_FOR_HUMAN_INPUT"
                    canonical.status = "WAITING_FOR_HUMAN_INPUT"
                elif not canonical.prescriptive_knowledge or not canonical.prescriptive_knowledge.prescriptions:
                    step.status = "FAILED"
                else:
                    presc = canonical.prescriptive_knowledge.prescriptions[-1]
                    # Check invalidation (already checked but keeping block structure)
                    if False:
                        canonical.conditions.append(StateCondition(
                            status="WAITING_FOR_HUMAN_INPUT",
                            reason_code="INVALIDATED_PRESCRIPTION",
                            message="Cannot generate action plan for invalidated prescription."
                        ))
                        step.status = "WAITING_FOR_HUMAN_INPUT"
                        canonical.status = "WAITING_FOR_HUMAN_INPUT"
                    else:
                        from .cognitive_engine import DeepSeekAdapter
                        engine = DeepSeekAdapter()
                        # LS81.2 — ROUTE UNIFICATION. The ActionPlan authority MUST come from
                        # canonical.human_decision (HITL), never from the LLM. Both ActionPlan routes
                        # (this one + EMActioner.execute_task) now enforce the SAME governed gate.
                        hd = getattr(canonical, "human_decision", None)
                        hd_sel = getattr(hd, "selected_alternative_id", None) if hd else None
                        hd_id = getattr(hd, "decision_id", None) if hd else None
                        needs_hitl = bool(getattr(presc, "human_decision_required", False)) or bool(hd)
                        if needs_hitl and (not hd or not hd_sel):
                            canonical.conditions.append(StateCondition(
                                status="WAITING_FOR_HUMAN_INPUT", reason_code="ACTION_PLAN_REQUIRES_HUMAN_DECISION",
                                message="No valid human decision for this ActionPlan; awaiting HITL authorization."))
                            step.status = "WAITING_FOR_HUMAN_INPUT"
                            canonical.status = "WAITING_FOR_HUMAN_INPUT"
                        else:
                            try:
                                # Generate ActionPlan (engine receives human_decision -> authoritative selection).
                                res = engine.propose_action_plan(canonical.problem, None, presc, hd)
                                from .action_model import ValidatedActionPlan
                                import uuid
                                plan = ValidatedActionPlan(
                                    plan_id=f"AP-{uuid.uuid4()}",
                                    prescription_ref=res.prescription_ref,
                                    selected_alternative_id=hd_sel or res.selected_alternative_id,
                                    human_decision_id=hd_id or res.human_decision_id,
                                    rationale=res.rationale,
                                    actions=res.proposed_actions,
                                    dependencies=res.dependencies,
                                    execution_conditions=res.execution_conditions,
                                    validity_conditions=res.validity_conditions,
                                    uncertainty=res.uncertainty,
                                    authority=presc.authority or "HUMAN",
                                    validation_status="VALIDATED"
                                )
                                if not hasattr(canonical, 'action_plan'):
                                    canonical.action_plan = None
                                canonical.action_plan = plan
                                step.status = "COMPLETED"
                            except Exception as e:
                                if "MISSING_MATHEMATICAL_SUPPORT" in str(e):
                                    canonical.conditions.append(StateCondition(
                                        status="WAITING_FOR_HUMAN_INPUT", reason_code="MISSING_MATHEMATICAL_SUPPORT",
                                        message="Action Plan requires unsupported quantitative claims."))
                                    step.status = "WAITING_FOR_HUMAN_INPUT"
                                    canonical.status = "WAITING_FOR_HUMAN_INPUT"
                                else:
                                    import traceback; traceback.print_exc()
                                    print(f"ACTION PLAN ERROR: {e}")
                                    step.status = "FAILED"
        elif step.capability_id == "frozen_knowledge.action_plan_verification":

            if not canonical.action_plan:
                if canonical.human_decision and canonical.human_decision.decision_type == "REJECT_ALL":
                    step.status = "COMPLETED"
                else:
                    step.status = "FAILED"
            else:
                plan = canonical.action_plan
                hd = canonical.human_decision
                cra = canonical.historical_context.cognitive_reevaluation if canonical.historical_context else None
                
                # 1. Alternative Mismatch (Test B)
                if plan.selected_alternative_id != hd.selected_alternative_id:
                    canonical.conditions.append(StateCondition(status="FAILED", reason_code="ACTION_PLAN_ALTERNATIVE_MISMATCH", message="Alternative mismatch"))
                    step.status = "FAILED"
                    canonical.status = "FAILED"
                # 2. Unauthorized Parameters (Test C) – Real validation against parameter contract
                elif getattr(hd, "parameters_modified", None):
                    from .parameter_validation import is_parameter_change_allowed
                    if not is_parameter_change_allowed(canonical, hd.parameters_modified):
                        canonical.conditions.append(StateCondition(status="FAILED", reason_code="UNAUTHORIZED_PARAMETER_CHANGE", message="Unauthorized parameter change"))
                        step.status = "FAILED"
                        canonical.status = "FAILED"
                # 3. Invalid Mathematical Basis (Test D)
                elif cra and cra.prescription_status in ["INVALIDATED", "INSUFFICIENT_DATA", "MISSING_PREDICTIVE_KNOWLEDGE"]:
                    canonical.conditions.append(StateCondition(status="BLOCKED", reason_code="MATHEMATICAL_SUPPORT_INVALID", message="Invalid mathematical basis"))
                    step.status = "FAILED"
                    canonical.status = "BLOCKED"
                # 4. Validity Violation (Test E)
                elif cra and isinstance(cra.validity_conditions, list) and any(isinstance(vc, dict) and vc.get("status") == "VIOLATED" for vc in cra.validity_conditions):
                    canonical.conditions.append(StateCondition(status="FAILED", reason_code="VALIDITY_DOMAIN_VIOLATION", message="Validity condition violation"))
                    step.status = "FAILED"
                    canonical.status = "FAILED"
                else:
                    plan.validation_status = "VALIDATED"
                    step.status = "COMPLETED"

        elif step.capability_id == "frozen_knowledge.evaluate_applicability":
            if canonical.historical_context:
                from .cognitive_engine import DeepSeekAdapter
                engine = DeepSeekAdapter()
                res = engine.evaluate_applicability(canonical.problem, canonical.historical_context)
                canonical.historical_context.applicability_assessment = res
                canonical.historical_context.applicability_status = res.assessment_status
                if res.human_review_required:
                    step.status = "WAITING_FOR_HUMAN_INPUT"
                else:
                    step.status = "COMPLETED"
            else:
                step.status = "COMPLETED" 

                    
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EMCore")

        elif step.capability_id == "evaluate_alternatives":
            task = None
            if canonical.problem and canonical.problem.structured_problem:
                task = next((t for t in canonical.problem.structured_problem.task_network.tasks if t.task_id == step.step_id), None)
            res = self.prescriptor.execute_task(canonical.problem, task, canonical)
            if hasattr(res, "conditions") and res.conditions:
                if any(c.status == "FAILED" for c in res.conditions):
                    raise RuntimeError("Prescriptor failed")
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EMPrescriptor")
            
        elif step.capability_id == "synthesize_information":
            self.analytics_engine.analyze(canonical)
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> AnalyticsEngine")
            
        elif step.capability_id in ["predict", "forecast", "predict_outcome", "analyze_dataset"]:
            self.predictor.execute(canonical, step)
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EMPredictor")

        elif step.capability_id == "execute_action":
            task = None
            if canonical.problem and canonical.problem.structured_problem:
                task = next((t for t in canonical.problem.structured_problem.task_network.tasks if t.task_id == step.step_id), None)
            res = self.actioner.execute_task(canonical.problem, task, canonical)
            if hasattr(res, "conditions") and res.conditions:
                if any(c.status == "FAILED" for c in res.conditions):
                    raise RuntimeError("Actioner failed")
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EMActioner")

        elif step.capability_id == "install_action":
            task = None
            if canonical.problem and canonical.problem.structured_problem:
                task = next((t for t in canonical.problem.structured_problem.task_network.tasks if t.task_id == step.step_id), None)
            res = self.installer.execute_task(canonical.problem, task, canonical)
            if hasattr(res, "conditions") and res.conditions:
                if any(c.status == "FAILED" for c in res.conditions):
                    raise RuntimeError("Installer failed")
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EMInstaller")

        elif step.capability_id in ["inspect_document", "extract_relevant_information", "analyze_evidence"]:
            # Needs evidence readiness check first
            readiness = EvidenceReadinessResolver.resolve(canonical, step)
            
            if readiness["status"] == "WAITING_FOR_EVIDENCE":
                step.status = "WAITING_FOR_EVIDENCE"
                canonical.waiting_reason = readiness["message"]
                canonical.waiting_for_evidence_ids = readiness.get("waiting_ids", [])
                return
                
            elif readiness["status"] == "GAP":
                step.status = "GAP"
                canonical.conditions.append(StateCondition(
                    status="GAP",
                    reason_code=readiness.get("reason_code", "EVIDENCE_MISSING"),
                    message=readiness["message"],
                    target=step.capability_id
                ))
                return
                
            elif readiness["status"] == "FAILED":
                step.status = "FAILED"
                canonical.conditions.append(StateCondition(
                    status="FAILED",
                    reason_code=readiness.get("reason_code", "SYSTEM_ERROR"),
                    message=readiness["message"],
                    target=step.capability_id
                ))
                return
            
            # Evidence is ready, route to EM Descriptor
            self.descriptor.execute(canonical, step)
            # LS94 — REQUEST MISSING DATA: when the Descriptor could not ground ANY finding and the
            # operation is a natural-question / knowledge / open-research one, ask the user for the
            # SPECIFIC missing data (blocking HITL) instead of publishing a thin/unsupported answer.
            if self._maybe_request_missing_data(canonical):
                canonical.status = "WAITING_FOR_HUMAN_INPUT"
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EMDescriptor")


        elif step.capability_id in ["generate_summary", "generate_presentation", "generate_report"]:
            task = None
            if canonical.problem and canonical.problem.structured_problem:
                task = next((t for t in canonical.problem.structured_problem.task_network.tasks if t.task_id == step.step_id), None)
            
            if step.capability_id in ["generate_summary", "generate_report"] and task and task.owner == "EM Publisher":
                res = self.publisher.execute_task(canonical.problem, task, canonical)
                if hasattr(res, "conditions") and res.conditions:
                    if any(c.status == "FAILED" for c in res.conditions):
                        raise RuntimeError("Publisher failed")
                # LS85: generate the governed story AFTER the result is available, so it reflects
                # the complete authoritative chain (human decision, sources, authority).
                self.story_engine.generate_story(canonical)
                step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EMPublisher")
            else:
                self.story_engine.generate_story(canonical)
                self.artifact_engine.generate_artifact(canonical)
                step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> Story/ArtifactEngine")
        else:
            # Simulated existing EM execution for everything else
            step.provenance.append(f"Work[{canonical.work.work_id}] -> Step[{step.step_id}] -> Capability[{step.capability_id}] -> Target[{step.target}] -> EM Simulated")

    def _compile_result(self, canonical: CanonicalWorkState):
        if canonical.result and canonical.result.status == "AVAILABLE":
            return # Result already compiled explicitly by publisher

        if not canonical.result:
            canonical.result = WorkResult(
                result_id=f"RES-{canonical.work.work_id}",
                work_id=canonical.work.work_id
            )
        
        # Determine if we have a real result
        has_acfl = bool(canonical.acfl.frontier) or bool(canonical.acfl.normalized_scores)
        has_extracted = bool(canonical.extracted_entities)
        op_mode = getattr(getattr(canonical, "problem", None), "operation_mode", "DECISION") or "DECISION"
        
        if has_acfl:
            canonical.result.status = "AVAILABLE"
            canonical.result.alternatives = canonical.problem.alternatives if canonical.problem else []
            canonical.result.scores = canonical.acfl.normalized_scores
            canonical.result.recommendations = canonical.acfl.frontier
            canonical.result.provenance.append("Derived from ACFL State")
        elif op_mode == "KNOWLEDGE_ANSWER":
            # LS92 — a natural-question answer must be AVAILABLE even when the pipeline produced
            # no numeric evaluation. Compile an HONEST semantic summary from the real canonical
            # data (question, real findings, real evaluation status). Never fabricates numbers,
            # decisions, or execution; it states NOT_EVALUATED / PENDING / NOT_EXECUTED truthfully.
            obj = (canonical.problem.objective if canonical.problem and getattr(canonical.problem, "objective", None) else None) \
                or (canonical.work.user_intent if canonical.work else "N/D")
            findings = [f.statement for f in canonical.knowledge.findings if getattr(f, "statement", None)]
            n_preds = len(getattr(canonical.predictive_knowledge, "predictions", None) or []) if canonical.predictive_knowledge else 0
            n_decided = sum(1 for d in getattr(canonical, "decision_points", None) or [] if getattr(d, "status", None) == "ANSWERED")
            has_plan = bool(getattr(canonical, "action_plan", None))
            lines = [f"Pregunta: {obj}"]
            lines.append(f"Hallazgos disponibles: {len(findings)}")
            for f in findings[:6]:
                lines.append(f"  · {f}")
            lines.append(f"Predicciones matemáticas: {n_preds} ({(n_preds and 'NOT_EVALUATED') or 'no evaluadas'})")
            # §9 consistency: the human/HITL state is DERIVED from the canonical state (never a
            # hardcoded "PENDIENTE" that can contradict the real request status).
            _hr_info = [r for r in (getattr(canonical, "human_requests", None) or [])
                        if getattr(r, "type", "") == "INFORMATION"]
            _hr_pending = [r for r in _hr_info if getattr(r, "status", "") == "PENDING"]
            _hr_answered = [r for r in _hr_info if getattr(r, "status", "") in ("ANSWERED", "COMPLETED")]
            _hr_suff = sorted({(getattr(r, "sufficiency_status", "NOT_EVALUATED") or "NOT_EVALUATED") for r in _hr_answered})
            lines.append(f"Solicitudes de información humana: {len(_hr_info)} (RESPONDIDAS={len(_hr_answered)}, "
                         f"PENDIENTES={len(_hr_pending)}"
                         + (f"; suficiencia: {', '.join(_hr_suff)}" if _hr_suff else "") + ")")
            lines.append(f"Decisión humana: {'registrada' if n_decided else 'no registrada'}")
            lines.append(f"Ejecución / plan de acción: {'presente' if has_plan else 'NO EJECUTADO'}")
            canonical.result.status = "AVAILABLE"
            canonical.result.summary = "\n".join(lines)
            canonical.result.findings = findings
            canonical.result.provenance.append("LS92 KNOWLEDGE_ANSWER fallback: semantic answer compiled from real state; math NOT_EVALUATED, decision PENDING, execution NOT_EXECUTED.")
        elif not has_extracted:
            # Since generate_summary handles its own result, if no ACFL and no extracted, it's unavailable
            canonical.result.status = "UNAVAILABLE"
            canonical.result.gaps.append("No actionable execution output.")
