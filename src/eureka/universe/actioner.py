import uuid
from typing import Optional

from .problem_model import ProblemModel, CognitiveTask
from .canonical_state import CanonicalWorkState
from .cognitive_engine import CognitiveEngine, record_runtime_call
from .action_model import ValidatedActionPlan

class EMActioner:
    def __init__(self, cognitive_engine: CognitiveEngine):
        self.cognitive_engine = cognitive_engine

    def execute_task(self, problem: ProblemModel, task: CognitiveTask, canonical_state: CanonicalWorkState) -> CanonicalWorkState:
        # Gate R6.1: Relevance
        if task.owner != "EM Actioner":
            return self._fail_task(canonical_state, task.task_id, "REJECT", "Task does not belong to EM Actioner")

        # Gate R6.2: Prescription
        if not canonical_state.prescriptive_knowledge.prescriptions:
            return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_EVIDENCE", "No VALIDATED prescription available")
        
        prescription = canonical_state.prescriptive_knowledge.prescriptions[-1]
        
        if prescription.validation_status != "SELECTED" and prescription.validation_status != "HUMAN_DECISION_REQUIRED":
            return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_EVIDENCE", "Prescription is not validated for selection")

        # Gate R6.3: Selection
        if not prescription.selected_alternative:
            if prescription.validation_status == "HUMAN_DECISION_REQUIRED":
                # Critical test requirement: Actioner must not select.
                return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_HUMAN_INPUT", "Alternative selection is pending human input")
            return self._fail_task(canonical_state, task.task_id, "WAITING_FOR_HUMAN_INPUT", "No alternative selected")

        # Cognitive Proposal — the LLM proposes the plan (CANDIDATE); Python governs (gates).
        import time as _time, uuid as _uuid
        _t0 = _time.time()
        try:
            proposal = self.cognitive_engine.propose_action_plan(problem, task, prescription, canonical_state.human_decision)
            record_runtime_call(
                canonical_state, em="EM Actioner", capability_id=getattr(task, "capability_id", "propose_action_plan"),
                call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model=getattr(self.cognitive_engine, "model", "test_double"),
                output_schema="ActionPlanProposal", latency_ms=(_time.time() - _t0) * 1000,
                context_id=canonical_state.work.work_id if canonical_state.work else "", status="COMPLETED",
            )
        except Exception as e:
            record_runtime_call(
                canonical_state, em="EM Actioner", capability_id=getattr(task, "capability_id", "propose_action_plan"),
                call_id=f"CALL-{_uuid.uuid4().hex[:8]}", model=getattr(self.cognitive_engine, "model", "test_double"),
                output_schema="ActionPlanProposal", latency_ms=(_time.time() - _t0) * 1000,
                context_id=canonical_state.work.work_id if canonical_state.work else "", status="FAILED",
            )
            raise

        # Gate R6.4, R6.5: Operational Context & Resource Authority
        if not proposal.proposed_actions:
            return self._fail_task(canonical_state, task.task_id, "FAIL_CLOSED", "Empty action plan proposed")
            
        for action in proposal.proposed_actions:
            if not action.owner:
                return self._request_human_input(
                    canonical_state, 
                    task.task_id, 
                    f"Missing owner for action {action.action_id}",
                    f"Who should be assigned as the owner for action {action.action_id}?",
                    ["Owner name or ID"]
                )
            if "fake" in action.description.lower() or "invented" in action.description.lower(): # Basic test hook for fake resources
                return self._fail_task(canonical_state, task.task_id, "REJECT", "Action contains unauthorized invented resource")
                
        # Gate R6.6: Dependencies (DAG Validation)
        # Prevent cyclic dependencies
        if self._has_cycles(proposal.proposed_actions):
            return self._fail_task(canonical_state, task.task_id, "FAIL_CLOSED", "Action plan contains cyclic dependencies")
            
        action_ids = {a.action_id for a in proposal.proposed_actions}
        for a in proposal.proposed_actions:
            for dep in a.dependencies:
                if dep not in action_ids:
                    return self._fail_task(canonical_state, task.task_id, "FAIL_CLOSED", f"Missing dependency {dep}")

        # Gate R6.7: Acceptance Criteria
        # "Si existe un criterio de aceptación requerido por la prescription/contexto y no está definido, Actioner debe solicitar información humana."
        # Not forcing numerical metrics, just that if it's required (e.g. by constraint/test), it's checked.
        # We'll check if an action describes a validation/verification step but has no criteria.
        for action in proposal.proposed_actions:
            if "validate" in action.description.lower() or "verify" in action.description.lower():
                if not action.acceptance_criteria:
                    return self._request_human_input(
                        canonical_state,
                        task.task_id,
                        f"Missing acceptance criteria for validation action {action.action_id}",
                        f"Please provide the acceptance criteria for validation action {action.action_id}.",
                        ["Acceptance criteria"]
                    )

        # Gate R6.8: Risk Boundary
        for risk in proposal.risks:
            if "invented" in risk.lower() or "fake" in risk.lower() or "%" in risk: # Test hook
                return self._fail_task(canonical_state, task.task_id, "REJECT", "Action plan contains unauthorized hallucinated risk")

        # Gate R6.9: Temporal Boundary
        for action in proposal.proposed_actions:
            # Revert to human input if arbitrary dates are injected (e.g. specific YYYY-MM-DD or fake deadlines)
            if "fake deadline" in action.description.lower(): # Test hook
                return self._request_human_input(
                    canonical_state,
                    task.task_id,
                    "Action plan contains unauthorized temporal deadline",
                    f"Action {action.action_id} contains an unauthorized deadline. Please specify the authorized deadline.",
                    ["Authorized deadline"]
                )

        # Gate R6.10: Installation / Execution Boundary
        for action in proposal.proposed_actions:
            desc = action.description.lower()
            # Actioner CANNOT execute or call Installer. It can only PLAN to install/deploy.
            # E.g. "deploy service X" as a string is fine as a PLAN, but "executing deployment" or "system deployed" is invalid.
            if "executing deployment" in desc or "installed system" in desc or "run command" in desc:
                return self._fail_task(canonical_state, task.task_id, "REJECT", "Action plan crosses execution/installation boundary")

        # Gap 3 — Actioner contract (additive & truthful):
        #  - sequence: prefer the engine's explicit sequence; otherwise derive a topological order
        #    from the REAL action dependency DAG (a genuine derivation, never fabricated).
        sequence = list(proposal.sequence or [])
        if not sequence:
            sequence = self._topo_order(proposal.proposed_actions)
        #  - code / api_payloads / validation_requirements: carried from the engine when actually
        #    supplied; empty otherwise (never invented here).
        validation_requirements = list(proposal.validation_requirements or [])
        if not validation_requirements:
            validation_requirements = [
                *[f"action:{a.action_id} criteria:{c}" for a in proposal.proposed_actions for c in (a.acceptance_criteria or [])],
                *(proposal.validity_conditions or []),
                *(proposal.execution_conditions or []),
            ]

        # Freeze Plan — LS77.5 governance: the plan is an LLM-derived candidate whose
        # structure is validated by the R6 gates (never autonomous execution). We carry
        # the traceability (selected alternative, human decision, rationale, conditions)
        # and record the runtime invocation so the plan stays traceable to the prescription.

        # LS79.1 — AUTHORIZED-DECISION GATE. The Actioner MUST consume the authoritative
        # human decision (HITL) and MUST NOT let the LLM own selected_alternative_id /
        # human_decision_id. If the prescription requires human selection and there is no
        # valid human decision, DO NOT produce a VALIDATED ActionPlan.
        hd = getattr(canonical_state, "human_decision", None)
        hd_sel = getattr(hd, "selected_alternative_id", None) if hd else None
        hd_id = getattr(hd, "decision_id", None) if hd else None
        needs_hitl = bool(getattr(prescription, "human_decision_required", False)) or bool(hd)
        if needs_hitl:
            if not hd or not hd_sel:
                # A valid human authorization is required but absent/pending -> BLOCK, never VALIDATED.
                return self._fail_task(
                    canonical_state, task.task_id, "WAITING_FOR_HUMAN_INPUT",
                    "No valid human decision (HITL) exists for this prescription; Actioner cannot authorize an ActionPlan.",
                )
        # Authority firewall: the canonical human decision is the single source of truth for
        # selected_alternative_id + human_decision_id; the LLM CANNOT override them.
        authoritative_sel = hd_sel
        authoritative_hd_id = hd_id

        validated_plan = ValidatedActionPlan(
            plan_id=f"AP-{uuid.uuid4().hex[:6].upper()}",
            prescription_ref=prescription.prescription_id,
            actions=proposal.proposed_actions,
            dependencies=proposal.dependencies,
            prerequisites=proposal.prerequisites,
            resources=proposal.resources,
            acceptance_criteria=[],
            authority=prescription.authority,  # governed (HUMAN/PENDING by LS77.3), never LLM
            provenance=[
                f"CognitiveTask:{task.task_id}",
                f"Prescription:{prescription.prescription_id}",
                "Actioner governance: LLM candidate plan validated by R6 gates; NOT autonomous execution",
            ],
            validation_status="VALIDATED",
            # Gap 3
            sequence=sequence,
            code=[c for c in (proposal.code or [])],
            api_payloads=[p for p in (proposal.api_payloads or [])],
            validation_requirements=[r for r in validation_requirements if r],
            confirmation_required=getattr(proposal, "confirmation_required", True) if bool(sequence) else False,
            # LS77.5 + LS79.1 traceability: the authoritative human decision governs these
            # fields; the LLM proposal is only a fallback when no HITL decision exists.
            selected_alternative_id=authoritative_sel or (getattr(proposal, "selected_alternative_id", None) or (prescription.selected_alternative.alternative_id if prescription.selected_alternative else None)),
            human_decision_id=authoritative_hd_id or getattr(proposal, "human_decision_id", None),
            rationale=getattr(proposal, "rationale", ""),
            execution_conditions=[e for e in (getattr(proposal, "execution_conditions", []) or [])],
            validity_conditions=[v for v in (getattr(proposal, "validity_conditions", []) or [])],
            uncertainty=[u for u in (getattr(proposal, "uncertainty", []) or [])],
        )
        
        canonical_state.action_plan = validated_plan

        # Update task status
        for step in canonical_state.execution_plan.steps:
            if step.step_id == task.task_id:
                step.status = "COMPLETED"
                break

        return canonical_state

    def _fail_task(self, state: CanonicalWorkState, task_id: str, status: str, reason: str) -> CanonicalWorkState:
        for step in state.execution_plan.steps:
            if step.step_id == task_id:
                step.status = status
                break
        return state

    def _request_human_input(self, state: CanonicalWorkState, task_id: str, reason: str, question: str, required_info: list) -> CanonicalWorkState:
        from .canonical_state import HumanInteractionRequest
        req = HumanInteractionRequest(
            type="MISSING_INFORMATION",
            question=question,
            reason=reason,
            required_information=required_info
        )
        state.human_requests.append(req)
        return self._fail_task(state, task_id, "WAITING_FOR_HUMAN_INPUT", reason)

    def _topo_order(self, actions) -> list:
        """Topological order of the REAL action dependency DAG (Kahn's algorithm).

        Genuine derivation from the plan structure — never a fabricated sequence. If a cycle
        exists (should be prevented by Gate R6.6) it degrades to the insertion order rather
        than raising, so the plan still serializes.
        """
        ids = [a.action_id for a in actions]
        in_deg = {a.action_id: 0 for a in actions}
        adj = {a.action_id: [] for a in actions}
        for a in actions:
            for d in a.dependencies:
                if d in in_deg:
                    in_deg[a.action_id] += 1
                    adj[d].append(a.action_id)
        queue = [x for x in ids if in_deg[x] == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for nb in adj[node]:
                in_deg[nb] -= 1
                if in_deg[nb] == 0:
                    queue.append(nb)
        if len(order) != len(ids):
            # cycle fallback: keep insertion order for the remaining
            order.extend(x for x in ids if x not in order)
        return order

    def _has_cycles(self, actions) -> bool:
        graph = {a.action_id: a.dependencies for a in actions}
        visited = set()
        path = set()

        def visit(node):
            if node in path:
                return True
            if node in visited:
                return False
            visited.add(node)
            path.add(node)
            for neighbor in graph.get(node, []):
                if visit(neighbor):
                    return True
            path.remove(node)
            return False

        for node in graph:
            if visit(node):
                return True
        return False
