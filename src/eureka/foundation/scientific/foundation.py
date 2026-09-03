import uuid
from typing import List
from eureka.foundation.scientific.models import (
    Alternative, ObjectivePredicate, EvaluationResult
)

class ScientificFoundation:
    """
    Deterministically evaluates predicates and alternatives using ACFL operations.
    Does NOT invent semantic logic or take decisions.
    """

    def evaluate_predicate(self, predicate: ObjectivePredicate, data: dict) -> float:
        """
        Evaluates an ObjectivePredicate on raw data.
        Returns the truth value [0.0, 1.0].
        """
        if predicate.evaluator:
            # We assume the evaluator operates over the mapped variables safely
            return float(predicate.evaluator(data))
        raise ValueError(f"Predicate {predicate.predicate_id} has no executable evaluator attached.")

    def evaluate_alternative(self, predicate: ObjectivePredicate, alternative: Alternative) -> EvaluationResult:
        """
        Evaluates an Alternative against an ObjectivePredicate.
        Returns an EvaluationResult representing the truth value and utility context.
        """
        tv = self.evaluate_predicate(predicate, alternative.data)
        
        # UTILITY SEMANTICS BOUNDARY
        # As established in LOOP 13, Truth Value = Utility ONLY IF authorized by the source
        # "Interpretability of a Logical Theory".
        
        utility_semantics = predicate.evaluation_semantics
        if utility_semantics == "ACFL_COMPOUND_PREDICATE_AS_UTILITY":
            utility_val = tv
            auth_src = "Interpretability of a Logical Theory"
        else:
            utility_val = None
            auth_src = "UNAUTHORIZED_UTILITY_EQUIVALENCE"

        return EvaluationResult(
            alternative_id=alternative.alternative_id,
            predicate_id=predicate.predicate_id,
            truth_value=tv,
            utility_value=utility_val,
            utility_semantics=utility_semantics,
            authority_source=auth_src,
            trace_id=str(uuid.uuid4()),
            provenance="ScientificFoundation.evaluate_alternative"
        )

    def truth_value(self, result: EvaluationResult) -> float:
        return result.truth_value

    def utility(self, result: EvaluationResult) -> float:
        if result.utility_value is None:
            raise ValueError(f"Utility is not authorized or undefined for EvaluationResult: {result.alternative_id}")
        return result.utility_value

    def compare(self, res1: EvaluationResult, res2: EvaluationResult) -> int:
        """
        Compares two EvaluationResults by their truth/utility value.
        Returns 1 if res1 > res2, -1 if res1 < res2, 0 if equal.
        """
        v1 = res1.utility_value if res1.utility_value is not None else res1.truth_value
        v2 = res2.utility_value if res2.utility_value is not None else res2.truth_value
        
        if v1 > v2: return 1
        elif v1 < v2: return -1
        return 0

    def rank(self, evaluations: List[EvaluationResult]) -> List[EvaluationResult]:
        """
        Orders the evaluations by highest value.
        This is a pure scientific operation (sort). It does NOT automatically select the 'best'.
        """
        # Sort descending by value
        return sorted(
            evaluations, 
            key=lambda r: r.utility_value if r.utility_value is not None else r.truth_value, 
            reverse=True
        )
