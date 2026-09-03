"""
EUREKA Canonical Mathematical Runtime: Generators

Provenance:
- LIR: LANGUAGE_IR.md
- Rules: CGR-002 (Abstract Interface Emission), CGR-005 (Purity Enforcement)
"""

from abc import ABC, abstractmethod
from .domains import TruthValue, GeneratorValue

class LogicalGenerator(ABC):
    """
    Pure Abstract Interface for an Additive Generator.
    
    Provenance:
    - LIR-ID: LIR-INTERFACE-LOGICAL-GENERATOR
    - RIR-ID: RIR-FUNCTION-001
    - MIR-ID: MIR-CONCEPT-LOGICAL-GENERATOR
    - TIR-ID: TIR-FUN-001
    - CMT-ID: CMT-FUN-001
    - CLAIM: c4f8d9b2...
    """
    
    @abstractmethod
    def evaluate(self, value: TruthValue) -> GeneratorValue:
        """
        Transforms a TruthValue to a GeneratorValue.
        Must preserve PURE semantics (no state mutation).
        """
        pass

class InverseGenerator(ABC):
    """
    Pure Abstract Interface for an Inverse Generator.
    
    Provenance:
    - LIR-ID: LIR-INTERFACE-INVERSE-GENERATOR
    - RIR-ID: RIR-FUNCTION-002
    - MIR-ID: MIR-CONCEPT-INVERSE-GENERATOR
    - TIR-ID: TIR-FUN-002
    - CMT-ID: CMT-FUN-002
    - CLAIM: c4f8d9b2...
    """
    
    @abstractmethod
    def evaluate(self, value: GeneratorValue) -> TruthValue:
        """
        Transforms a GeneratorValue back to a TruthValue.
        Must preserve PURE semantics (no state mutation).
        """
        pass

import math

class CMTGenerator001(LogicalGenerator):
    """
    Concrete implementation of CMT-GENERATOR-001 (g(x) = -ln(x))
    LIMIT_EXTENSION at x=0 represented as math.inf in Backend
    """
    def evaluate(self, value: TruthValue) -> GeneratorValue:
        if value == 0.0:
            return math.inf
        return -math.log(value)

class CMTInverseGenerator001(InverseGenerator):
    """
    Concrete implementation of CMT-GENERATOR-001 Inverse (g^-1(y) = exp(-y))
    """
    def evaluate(self, value: GeneratorValue) -> TruthValue:
        return math.exp(-value)

class CMTGenerator002(LogicalGenerator):
    """
    Concrete implementation of CMT-GENERATOR-002 (g_D(x) = -ln(1-x))
    LIMIT_EXTENSION at x=1 represented as math.inf in Backend
    """
    def evaluate(self, value: TruthValue) -> GeneratorValue:
        if value == 1.0:
            return math.inf
        return -math.log(1.0 - value)

class CMTInverseGenerator002(InverseGenerator):
    """
    Concrete implementation of CMT-GENERATOR-002 Inverse (g_D^-1(y) = 1 - exp(-y))
    """
    def evaluate(self, value: GeneratorValue) -> TruthValue:
        return 1.0 - math.exp(-value)

class CMTGenerator003(LogicalGenerator):
    """
    Concrete implementation of CMT-GENERATOR-003 (g(x) = 1 - x)
    (Formula 006: Arithmetic-Mean-Based Compensatory Conjunction)
    """
    def evaluate(self, value: TruthValue) -> GeneratorValue:
        return 1.0 - value

class CMTInverseGenerator003(InverseGenerator):
    """
    Concrete implementation of CMT-GENERATOR-003 Inverse (g^-1(y) = 1 - y)
    """
    def evaluate(self, value: GeneratorValue) -> TruthValue:
        return 1.0 - value
