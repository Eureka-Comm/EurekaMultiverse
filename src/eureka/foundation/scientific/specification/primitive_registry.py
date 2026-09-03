from typing import Dict, Any

class PrimitiveRegistry:
    """
    Read-only catalog mapping semantic mathematical intentions
    to the already-certified backend primitives in `generators.py` and `operators.py`.
    """
    def __init__(self):
        # Maps generator identities to concrete classes without importing them immediately
        self._generators = {
            "CMT-GENERATOR-001": "src.eureka.math.generators.CMTGenerator001",
            "CMT-INVERSE-001": "src.eureka.math.generators.CMTInverseGenerator001",
            "CMT-GENERATOR-002": "src.eureka.math.generators.CMTGenerator002",
            "CMT-INVERSE-002": "src.eureka.math.generators.CMTInverseGenerator002",
            "CMT-GENERATOR-003": "src.eureka.math.generators.CMTGenerator003",
            "CMT-INVERSE-003": "src.eureka.math.generators.CMTInverseGenerator003",
        }
        
        self._operators = {
            "CONJUNCTION": "src.eureka.math.operators.Conjunction",
            "DISJUNCTION": "src.eureka.math.operators.Disjunction"
        }
        
    def resolve_generator(self, identity: str) -> str:
        if identity not in self._generators:
            raise KeyError(f"Generator identity {identity} not found in certified primitive catalog.")
        return self._generators[identity]
        
    def resolve_operator(self, identity: str) -> str:
        if identity not in self._operators:
            raise KeyError(f"Operator identity {identity} not found in certified primitive catalog.")
        return self._operators[identity]
