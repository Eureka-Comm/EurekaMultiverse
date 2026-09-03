from typing import Dict, List, Any
from src.eureka.foundation.scientific.models import (
    SemanticDecisionContext,
    ObjectivePredicateSpec,
    SemanticAuthorityType,
    ConfirmationStatus
)

class ObjectivePredicateBuilder:
    """
    Builder responsible for generating an ObjectivePredicateSpec from a SemanticDecisionContext.
    Enforces the semantic authority boundary by not inventing mappings.
    """
    
    def build(self, context: SemanticDecisionContext, predicate_id: str) -> dict:
        """
        Attempts to build an ObjectivePredicateSpec.
        Returns a dict containing 'status', 'missing_inputs' (if any), and 'spec' (if partial/complete).
        """
        # Validate minimum semantics
        missing = []
        if not context.preferences:
            missing.append("preferences")
            
        if missing:
            return {
                "status": "INCOMPLETE_SEMANTIC_AUTHORITY",
                "missing_inputs": missing,
                "spec": None
            }
            
        # Proceed to partial build if we have some preferences
        variables = []
        operators = []
        candidate_mappings = {}
        
        # Methodological rule (KDBKE):
        # Constraints -> AND (Candidate)
        # Alternatives -> OR (Candidate)
        # Priorities -> Modifier (Candidate)
        
        # Here we do NOT commit them to final without authority, but we propose them.
        for constraint in context.constraints:
            candidate_mappings[constraint] = "Conjunction (AND)"
            operators.append("AND")
        
        for pref in context.preferences:
            candidate_mappings[pref] = "Disjunction (OR) or Modifiers"
            # It's a heuristic candidate mapping
            operators.append("OR")
            
        for p in context.priorities:
            candidate_mappings[p] = "Modifier"
            operators.append("MODIFIER")
            
        # We need a formal semantic authority to go further.
        # Check if the context already has DOCUMENT or HUMAN authority
        if context.authority_type in [SemanticAuthorityType.DOCUMENT, SemanticAuthorityType.HUMAN]:
            conf_status = ConfirmationStatus.CONFIRMED
            status_str = "READY_FOR_VALIDATION"
        elif context.authority_type == SemanticAuthorityType.LLM:
            conf_status = ConfirmationStatus.PENDING
            status_str = "SEMANTIC_AUTHORITY_REQUIRED"
        else:
            conf_status = ConfirmationStatus.UNVERIFIED
            status_str = "PARTIAL_OBJECTIVE_PREDICATE"
            
        spec = ObjectivePredicateSpec(
            predicate_id=predicate_id,
            variables=variables,
            goals=context.goals,
            preferences=context.preferences,
            constraints=context.constraints,
            priority_structure={p: "unknown_weight" for p in context.priorities},
            candidate_mappings=candidate_mappings,
            logical_structure="Pending Authorization",
            operators=list(set(operators)),
            authority_source=context.authority_source,
            semantic_authority=context.authority_type,
            confirmation_status=conf_status,
            provenance="Builder: Heuristic Extraction",
            validation_status="UNVERIFIED"
        )
        
        return {
            "status": status_str,
            "missing_inputs": [],
            "spec": spec
        }
