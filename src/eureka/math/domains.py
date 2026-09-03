"""
EUREKA Canonical Mathematical Runtime: Domains

Provenance:
- LIR: LANGUAGE_IR.md
- Rules: CGR-001 (Immutable Numeric Value Emission)
"""

from dataclasses import dataclass
from typing import Any
from .exceptions import DomainError

@dataclass(frozen=True)
class TruthValue:
    """
    Immutable Representation of a Truth Value.
    
    Provenance:
    - LIR-ID: LIR-TYPE-TRUTH-VALUE
    - RIR-ID: RIR-VALUE-001
    - MIR-ID: MIR-CONCEPT-TRUTH-SPACE
    - TIR-ID: TIR-DOM-001
    - CMT-ID: CMT-DOM-001
    - CLAIM: e8a2b5f1...
    """
    value: float
    
    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise DomainError(f"Truth value must be in [0, 1], got {self.value}")

@dataclass(frozen=True)
class GeneratorValue:
    """
    Immutable Representation of a value in the Generator Space.
    
    Provenance:
    - LIR-ID: LIR-TYPE-GENERATOR-VALUE
    - RIR-ID: RIR-VALUE-002
    - MIR-ID: MIR-CONCEPT-GENERATOR-SPACE
    - TIR-ID: TIR-DOM-003
    - CMT-ID: CMT-DOM-003
    - CLAIM: c4f8d9b2...
    """
    value: float
    
    def __post_init__(self) -> None:
        if self.value < 0.0:
            raise DomainError(f"Generator value must be >= 0, got {self.value}")
