from typing import Dict, Any
from src.eureka.foundation.scientific.models import (
    ObjectivePredicateSpec,
    ConfirmationStatus,
    SemanticAuthorityType
)

class ObjectivePredicateValidator:
    """
    Validates an ObjectivePredicateSpec to ensure it complies with the mathematical 
    and semantic boundaries defined by the architecture.
    """
    
    ALLOWED_OPERATORS = ["AND", "OR", "NOT", "MODIFIER", "ProductAnd", "Disjunction-CMT", "CompensatoryAnd"]

    def validate(self, spec: ObjectivePredicateSpec) -> dict:
        """
        Validates the spec against structural, mathematical, and authority constraints.
        Returns a dict with 'is_valid' and 'reasons'.
        """
        reasons = []
        is_valid = True
        
        # A. STRUCTURAL VALIDITY
        if not spec.predicate_id:
            is_valid = False
            reasons.append("Missing predicate_id")
            
        # B. MATHEMATICAL EVALUABILITY
        if spec.logical_structure == "Pending Authorization":
            is_valid = False
            reasons.append("Formula not evaluable (Pending Authorization)")
            
        # C. OPERATOR VALIDITY
        for op in spec.operators:
            if op not in self.ALLOWED_OPERATORS:
                is_valid = False
                reasons.append(f"Unknown operator: {op}")
                
        # D. VARIABLE COMPLETENESS
        # Since it's an abstract check, we just check that the list is present
        # In a real system we would verify against the dataset
        if not spec.variables and spec.logical_structure != "Pending Authorization":
            # Must have variables if authorized
            is_valid = False
            reasons.append("Missing variables")
            
        # E. SEMANTIC AUTHORITY
        if spec.semantic_authority == SemanticAuthorityType.UNVERIFIED:
            is_valid = False
            reasons.append("Semantic authority is UNVERIFIED")
            
        # F. PROVENANCE
        if not spec.provenance:
            is_valid = False
            reasons.append("Missing provenance")
            
        # G. CONFIRMATION STATUS
        if spec.confirmation_status != ConfirmationStatus.CONFIRMED:
            is_valid = False
            reasons.append(f"Confirmation status is {spec.confirmation_status.value}")
            
        return {
            "is_valid": is_valid,
            "reasons": reasons
        }
