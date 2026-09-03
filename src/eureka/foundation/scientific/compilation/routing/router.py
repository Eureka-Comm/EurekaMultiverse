from .taxonomy import TaxonomicDecision, TaxonomicFamily, RoutingState
from .exceptions import ArchitecturalRoutingRejection, UnresolvedTaxonomyError
from .provenance import TopologicalTracker

class RoutingDecision:
    def __init__(self, state: RoutingState, target_route: str, taxonomy: TaxonomicDecision):
        self.state = state
        self.target_route = target_route
        self.taxonomy = taxonomy

class Router:
    """
    Physical Runtime Boundary for Routing.
    Consumes a TaxonomicDecision and returns a RoutingDecision.
    Does NOT classify.
    """
    
    def route(self, decision: TaxonomicDecision, target: str, tracker: TopologicalTracker = None) -> RoutingDecision:
        """
        Determines if the target route is valid for the given taxonomy.
        target should be "PRIMITIVE" or "DERIVED".
        """
        if tracker:
            tracker.increment_metric("router_calls")
            
        if decision.family == TaxonomicFamily.UNKNOWN:
            if tracker:
                tracker.log("ROUTE", "UNRESOLVED", "Taxonomy is UNKNOWN", target, "BLOCKED")
            raise UnresolvedTaxonomyError("Taxonomy is UNKNOWN; cannot route formula.")
            
        if decision.family == TaxonomicFamily.FAMILY_A_PRIMITIVE:
            if target == "PRIMITIVE":
                if tracker:
                    tracker.increment_metric("primitive_route")
                    tracker.log("ROUTE", "RESOLVED", "Taxonomy A matches Primitive", target, "PASS")
                return RoutingDecision(RoutingState.RESOLVED, target, decision)
            else:
                if tracker:
                    tracker.log("ROUTE", "REJECTED", "Taxonomy A cannot go to Derived", target, "BLOCKED")
                raise ArchitecturalRoutingRejection("FAMILY_A_PRIMITIVE cannot be routed to DERIVED.")
                
        if decision.family == TaxonomicFamily.FAMILY_B_DERIVED:
            if target == "DERIVED":
                if tracker:
                    tracker.increment_metric("derived_route")
                    tracker.log("ROUTE", "RESOLVED", "Taxonomy B matches Derived", target, "PASS")
                return RoutingDecision(RoutingState.RESOLVED, target, decision)
            else:
                if tracker:
                    tracker.log("ROUTE", "REJECTED", "Taxonomy B cannot go to Primitive", target, "BLOCKED")
                raise ArchitecturalRoutingRejection("FAMILY_B_DERIVED cannot be routed to PRIMITIVE.")
                
        raise ArchitecturalRoutingRejection("Invalid routing state.")
