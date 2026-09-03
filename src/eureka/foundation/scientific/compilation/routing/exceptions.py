class EUREKAArchitecturalException(Exception):
    """Base class for all architectural rejections in EUREKA."""
    pass

class ArchitecturalRoutingRejection(EUREKAArchitecturalException):
    """
    Raised when a formula attempts to enter a route forbidden by its Taxonomy.
    e.g., F005 -> Primitive.
    Provenance: Phase 12.6 Routing Rejection Semantics.
    """
    pass

class UnresolvedTaxonomyError(EUREKAArchitecturalException):
    """
    Raised when routing is attempted on an UNKNOWN taxonomy.
    """
    pass

class AdmissionRejection(EUREKAArchitecturalException):
    """
    Raised when a route is authorized, but the specific compiler contract rejects the formula.
    """
    pass
