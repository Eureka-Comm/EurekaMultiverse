from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TaxonomicFamily(Enum):
    """
    Taxonomic family of a formula, strictly decoupled from compiler availability.
    Provenance: Phase 12.2 Family Taxonomy Contract.
    """
    FAMILY_A_PRIMITIVE = "FAMILY_A_PRIMITIVE"
    FAMILY_B_DERIVED = "FAMILY_B_DERIVED"
    UNKNOWN = "UNKNOWN"

class RoutingState(Enum):
    """
    State of the routing decision.
    Provenance: Phase 12.3 Routing Decision Contract.
    """
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    UNRESOLVED = "UNRESOLVED"

@dataclass(frozen=True)
class StructuralEvidence:
    """
    Physical representation of the mathematical topology of a formula.
    Classification input parameter.
    Arity is strictly descriptive and does not decide taxonomy.
    """
    arity: str  # "UNARY", "BINARY", "N-ARY", etc.
    has_own_compatible_generator: bool
    is_homogeneous_topology: bool
    primitive_compatible_mapping: bool
    has_external_dependency: bool
    requires_composition: bool
    requires_dag: bool

@dataclass(frozen=True)
class TaxonomicDecision:
    """
    The auditable result of a classification operation.
    """
    family: TaxonomicFamily
    structural_basis: StructuralEvidence
    satisfied_criteria: tuple[str, ...]
    unsatisfied_criteria: tuple[str, ...]
    contradictory_criteria: tuple[str, ...]
    composition_status: str
    classification_provenance: str
