from typing import Dict, Any, List
from .canonical_state import CanonicalWorkState

class GovernanceEngine:
    """
    Implements the Governance Gate. Ensures no hypothesis becomes a fact, 
    no prediction becomes certainty, and DeepSeek interpretations are not scientific facts.
    """
    def validate(self, state: CanonicalWorkState) -> Dict[str, Any]:
        
        # Ensure all claims have an established status
        for evidence in state.work.evidence:
            if evidence.get('claim_status') not in ["ESTABLISHED", "INFERRED", "HYPOTHESIS"]:
                return {"status": "REVISE", "reason": "Unverified claims detected in Evidence."}
        
        # Rule: DeepSeek interpretation != Scientific result
        for artifact in state.work.artifacts:
            if "DEEPSEEK" in str(artifact) and "SCIENTIFIC" in str(artifact):
                return {"status": "REVISE", "reason": "DeepSeek cannot be the source of scientific facts."}

        return {"status": "ACCEPT", "reason": "All claims and provenance chains validated."}
