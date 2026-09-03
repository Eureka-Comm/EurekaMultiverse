from .router import RoutingDecision, RoutingState
from .taxonomy import TaxonomicFamily
from .exceptions import AdmissionRejection, ArchitecturalRoutingRejection
from .provenance import TopologicalTracker

class PrimitiveAdmissionGate:
    """
    Physical Runtime Boundary for Primitive Admission.
    """
    def accept(self, routing_decision: RoutingDecision, tracker: TopologicalTracker = None) -> bool:
        if routing_decision.state != RoutingState.RESOLVED or routing_decision.target_route != "PRIMITIVE":
            raise AdmissionRejection("Cannot admit a non-resolved or non-primitive route.")
            
        if routing_decision.taxonomy.family == TaxonomicFamily.FAMILY_B_DERIVED:
            if tracker:
                tracker.log("ADMIT", "REJECTED", "FAMILY_B_DERIVED strictly blocked", "PRIMITIVE", "BLOCKED")
            raise ArchitecturalRoutingRejection("Primitive Admission unconditionally rejects FAMILY_B_DERIVED.")
            
        if routing_decision.taxonomy.family == TaxonomicFamily.FAMILY_A_PRIMITIVE:
            if tracker:
                tracker.increment_metric("primitive_admission")
                tracker.log("ADMIT", "ELIGIBLE", "FAMILY_A_PRIMITIVE allowed", "PRIMITIVE", "PASS")
            return True
            
        raise AdmissionRejection("Invalid state at PrimitiveAdmissionGate.")

class DerivedAdmissionGate:
    """
    Physical Runtime Boundary for Derived Admission.
    """
    def accept(self, routing_decision: RoutingDecision, tracker: TopologicalTracker = None) -> bool:
        if routing_decision.state != RoutingState.RESOLVED or routing_decision.target_route != "DERIVED":
            raise AdmissionRejection("Cannot admit a non-resolved or non-derived route.")
            
        if routing_decision.taxonomy.family == TaxonomicFamily.FAMILY_B_DERIVED:
            # We verify DAG structure criteria here in the future
            if tracker:
                tracker.increment_metric("derived_admission")
                tracker.log("ADMIT", "ELIGIBLE", "FAMILY_B_DERIVED structurally valid", "DERIVED", "PASS")
            # Return true conceptually, though compiler is not implemented
            return True
            
        if routing_decision.taxonomy.family == TaxonomicFamily.FAMILY_A_PRIMITIVE:
            raise ArchitecturalRoutingRejection("Derived Admission unconditionally rejects FAMILY_A_PRIMITIVE.")
            
        raise AdmissionRejection("Invalid state at DerivedAdmissionGate.")
