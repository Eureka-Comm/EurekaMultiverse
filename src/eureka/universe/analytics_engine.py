from typing import Dict, Any, List
from .canonical_state import CanonicalWorkState

class ExplanatoryAnalyticsEngine:
    """
    Implements Explanatory Analytics.
    Answers WHAT, WHY, WHAT CHANGED, WHAT DRIVES IT, WHAT IF, HOW CONFIDENT, WHAT IS MISSING 
    directly from CanonicalWorkState.
    """
    def analyze(self, state: CanonicalWorkState):
        if not state.result:
            return
            
        analysis = {
            "WHAT": "Execution result compiled.",
            "WHY": [],
            "WHAT_CHANGED": "Initial execution.",
            "WHAT_DRIVES_IT": [],
            "WHAT_IF": [],
            "HOW_CONFIDENT": state.result.confidence if state.result.confidence else "Unknown",
            "WHAT_IS_MISSING": state.result.gaps
        }
        
        if state.acfl.frontier:
            analysis["WHAT"] = f"Top alternatives identified: {', '.join(state.acfl.frontier)}"
            analysis["WHY"] = [f"Weights: {state.acfl.weights}"]
            
        state.result.findings.append(analysis)
