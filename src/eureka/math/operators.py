"""
EUREKA Canonical Mathematical Runtime: Operators

Provenance:
- LIR: LANGUAGE_IR.md
- Rules: CGR-002 (Abstract Interface), CGR-003 (Iterable)
"""

from abc import ABC, abstractmethod
from typing import Iterable
from .domains import TruthValue
from .generators import LogicalGenerator, InverseGenerator

class Conjunction:
    """
    Pure Abstract Interface for a Compensatory Conjunction Operator.
    
    Provenance:
    - LIR-ID: LIR-INTERFACE-CONJUNCTION
    - RIR-ID: RIR-OPERATOR-001
    - MIR-ID: MIR-CONCEPT-CONJUNCTION
    - TIR-ID: TIR-OP-001
    - CMT-ID: CMT-OP-001
    - CLAIM: a1b2c3d4...
    
    Dependencies:
    Requires injection of LogicalGenerator and InverseGenerator.
    """
    
    def __init__(
        self, 
        generator: LogicalGenerator, 
        inverse_generator: InverseGenerator
    ) -> None:
        self.generator = generator
        self.inverse_generator = inverse_generator
        
    def aggregate(self, values: Iterable[TruthValue]) -> TruthValue:
        """
        Aggregates a sequence of TruthValues into a single TruthValue.
        Must preserve PURE semantics (no state mutation).
        Validation Policy: ValueError on range boundary violation or empty sequence.
        """
        truth_values = tuple(values)
        
        # Validation: Cardinality (n >= 1)
        if not truth_values:
            raise ValueError("Conjunction requires at least one truth value")
            
        # Validation: Domain ([0, 1])
        for x in truth_values:
            if not (0.0 <= x <= 1.0):
                raise ValueError("Truth values must be in [0, 1]")
                
        # Forward Mapping
        mapped_values = (
            self.generator.evaluate(x)
            for x in truth_values
        )
        
        # Substrate Aggregation
        generator_sum = sum(mapped_values)
        
        n = len(truth_values)
        inverse_n = 1.0 / n
        generator_mean = generator_sum * inverse_n
        
        # Inverse Mapping
        result = self.inverse_generator.evaluate(generator_mean)
        
        return result

class Disjunction:
    """
    Pure Abstract Interface for a Compensatory Disjunction Operator.
    
    Provenance:
    - LIR-ID: LIR-INTERFACE-DISJUNCTION
    - CMT-ID: CMT-OP-002
    
    Dependencies:
    Requires injection of LogicalGenerator and InverseGenerator.
    """
    
    def __init__(
        self, 
        generator: LogicalGenerator, 
        inverse_generator: InverseGenerator
    ) -> None:
        self.generator = generator
        self.inverse_generator = inverse_generator
        
    def aggregate(self, values: Iterable[TruthValue]) -> TruthValue:
        """
        Aggregates a sequence of TruthValues into a single TruthValue.
        Must preserve PURE semantics (no state mutation).
        Validation Policy: ValueError on range boundary violation or empty sequence.
        """
        truth_values = tuple(values)
        
        # Validation: Cardinality (n >= 1)
        if not truth_values:
            raise ValueError("Disjunction requires at least one truth value")
            
        # Validation: Domain ([0, 1])
        for x in truth_values:
            if not (0.0 <= x <= 1.0):
                raise ValueError("Truth values must be in [0, 1]")
                
        # Forward Mapping
        mapped_values = (
            self.generator.evaluate(x)
            for x in truth_values
        )
        
        # Substrate Aggregation
        generator_sum = sum(mapped_values)
        
        n = len(truth_values)
        inverse_n = 1.0 / n
        generator_mean = generator_sum * inverse_n
        
        # Inverse Mapping
        result = self.inverse_generator.evaluate(generator_mean)
        
        return result
