"""
EUREKA Canonical Mathematical Runtime: Exceptions

Provenance:
- LIR: LANGUAGE_IR.md (LIR-ERROR-DOMAIN, LIR-ERROR-INVARIANT)
- Rules: CGR-004
"""

class DomainError(ValueError):
    """
    Exception raised for operations violating boundary constraints.
    
    Provenance:
    - LIR-ID: LIR-ERROR-DOMAIN
    - RIR-ID: RIR-VAL-001, RIR-VAL-002
    - MIR-ID: TIR-VAL-002 (Domain Boundary)
    - CMT-ID: CMT-CON-001
    """
    pass

class InvariantError(RuntimeError):
    """
    Fatal exception raised for operations breaching mathematical invariants.
    
    Provenance:
    - LIR-ID: LIR-ERROR-INVARIANT
    - RIR-ID: RIR-VAL-003
    - MIR-ID: TIR-VAL-001 (Range Check)
    - CMT-ID: CMT-INV-001
    """
    pass
