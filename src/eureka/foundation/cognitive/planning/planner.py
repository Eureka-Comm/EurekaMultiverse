from typing import List, Dict, Optional
from eureka_cognitive_sdk.core.exceptions.enterprise import EnterpriseError
from eureka_cognitive_sdk.core.utilities.result import Result
from eureka.foundation.cognitive.contracts.intent import EnterpriseIntent
from eureka.foundation.cognitive.contracts.execution_plan import ExecutionPlan
from eureka.foundation.cognitive.orchestration.em_registry import EMRegistry
from src.eureka.foundation.scientific.runtime.assembly import CapabilityRegistry

class ExecutionPlanValidator:
    def __init__(self, em_registry: EMRegistry, capability_registry: CapabilityRegistry):
        self._em_registry = em_registry
        self._capability_registry = capability_registry

    def validate(self, plan: ExecutionPlan) -> Result[ExecutionPlan, EnterpriseError]:
        # Verify EM is registered
        if not self._em_registry.contains(plan.selected_em_id):
            return Result.fail(EnterpriseError(f"Validation failed: EM {plan.selected_em_id} not registered"))
            
        # Verify EM metadata matches plan
        em = self._em_registry.resolve(plan.selected_em_id)
        if em.get_semantic_metadata().version != plan.em_version:
            return Result.fail(EnterpriseError("Validation failed: EM version mismatch"))
            
        # Verify required capabilities exist in the capability registry
        for req in plan.required_capabilities:
            try:
                cap = self._capability_registry.resolve(req.requirement_id)
                if not cap:
                    return Result.fail(EnterpriseError(f"Validation failed: Required capability {req.requirement_id} is missing in registry"))
            except Exception as e:
                return Result.fail(EnterpriseError(f"Validation failed: Required capability {req.requirement_id} error: {e}"))
                
        # Validate constraints
        for constraint_key, constraint_val in plan.intent.constraints.items():
            em_constraints = em.get_semantic_metadata().constraints
            if constraint_key in em_constraints and em_constraints[constraint_key] != constraint_val:
                return Result.fail(EnterpriseError(f"Validation failed: Constraint mismatch on {constraint_key}"))

        plan.validation_status = "VALID"
        return Result.ok(plan)


class CognitivePlanner:
    def __init__(self, em_registry: EMRegistry, capability_registry: CapabilityRegistry, planner_id: str):
        self._em_registry = em_registry
        self._capability_registry = capability_registry
        self._planner_id = planner_id
        self._validator = ExecutionPlanValidator(em_registry, capability_registry)

    def generate_plan(self, intent: EnterpriseIntent) -> Result[ExecutionPlan, EnterpriseError]:
        # 1. Discover Candidate EMs
        candidates = self._em_registry.discover(intent)
        if not candidates:
            return Result.fail(EnterpriseError("No candidate EM found to fulfill intent"))
            
        # 2. Select Candidate (Pick first valid for now, or rank)
        selected_em = candidates[0]
        meta = selected_em.get_semantic_metadata()
        
        # 3. Capability Planning
        requirements = selected_em.get_capability_requirements()
        
        # 4. Explainability / Rationale
        rejected = [c.em_id for c in candidates[1:]]
        rationale = (
            f"WHY THIS EM? "
            f"intent: {intent.objective} on {intent.domain} | "
            f"candidate EM: {selected_em.em_id} | "
            f"semantic match: {meta.semantic_domain} | "
            f"required outputs: {', '.join(meta.produced_knowledge_types)} | "
            f"capabilities: {', '.join(r.requirement_id for r in requirements)} | "
            f"constraints: {meta.constraints} | "
            f"rejected alternatives: {', '.join(rejected) if rejected else 'None'} | "
            f"final decision: MATCH"
        )
        
        # 5. Construct ExecutionPlan
        plan = ExecutionPlan(
            intent=intent,
            selected_em_id=selected_em.em_id,
            em_version=meta.version,
            required_capabilities=requirements,
            rationale=rationale,
            provenance_requirements=intent.evidence_requirements,
            planner_id=self._planner_id
        )
        
        # 6. Validate Plan
        return self._validator.validate(plan)
