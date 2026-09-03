from typing import Tuple, List
from .taxonomy import TaxonomicFamily, StructuralEvidence, TaxonomicDecision

class Classifier:
    """
    Physical runtime boundary for Semantic Classification.
    Provenance: Phase 12.1 and 12.2.
    Implements evidence-based classification without compiler probing.
    """
    
    def classify(self, evidence: StructuralEvidence, formula_id: str = "Anonymous", tracker=None) -> TaxonomicDecision:
        """
        Evaluates structural evidence to produce a deterministic TaxonomicDecision.
        """
        if tracker:
            tracker.increment_metric("classifier_calls")
            
        # Family-A specific criteria
        family_a_evidence = [
            ("OwnCompatibleGenerator", evidence.has_own_compatible_generator == True),
            ("HomogeneousTopology", evidence.is_homogeneous_topology == True),
            ("PrimitiveCompatibleMapping", evidence.primitive_compatible_mapping == True),
            ("ExternalDependency", evidence.has_external_dependency == False),
            ("CompositionRequired", evidence.requires_composition == False),
        ]
        
        # Family-B specific criteria
        family_b_evidence = [
            ("CompositionRequired", evidence.requires_composition == True),
            ("DAGRequired", evidence.requires_dag == True),
            ("ExternalDependency", evidence.has_external_dependency == True),
            ("OwnCompatibleGenerator", evidence.has_own_compatible_generator == False),
            ("PrimitiveCompatibleMapping", evidence.primitive_compatible_mapping == False),
        ]
        
        is_family_a = all(satisfied for _, satisfied in family_a_evidence)
        is_family_b = all(satisfied for _, satisfied in family_b_evidence)
        
        satisfied_criteria: List[str] = []
        unsatisfied_criteria: List[str] = []
        contradictory_criteria: List[str] = []
        
        # Identify specific contradictions (e.g., claims own generator but also requires composition)
        if evidence.has_own_compatible_generator and evidence.requires_composition:
            contradictory_criteria.append("OwnCompatibleGenerator AND CompositionRequired")
            
        if evidence.is_homogeneous_topology and evidence.requires_dag:
            contradictory_criteria.append("HomogeneousTopology AND DAGRequired")
            
        # Determine Family
        family = TaxonomicFamily.UNKNOWN
        if is_family_a and not is_family_b and not contradictory_criteria:
            family = TaxonomicFamily.FAMILY_A_PRIMITIVE
            satisfied_criteria = [c[0] for c in family_a_evidence]
        elif is_family_b and not is_family_a and not contradictory_criteria:
            family = TaxonomicFamily.FAMILY_B_DERIVED
            satisfied_criteria = [c[0] for c in family_b_evidence]
        else:
            # UNKNOWN logic due to missing or contradictory evidence
            family = TaxonomicFamily.UNKNOWN
            if is_family_a and is_family_b:
                contradictory_criteria.append("Satisfies both Family-A and Family-B (Impossible overlap)")
                
            # If not A and not B, we list what failed
            if not is_family_a and not is_family_b:
                unsatisfied_criteria = ["Missing full evidence for A and B"]
        
        composition_status = "DAG" if evidence.requires_dag else "Atomic"
        if family == TaxonomicFamily.UNKNOWN:
            composition_status = "Unresolved"
            
        provenance = f"CLASSIFY: {formula_id} evaluated at Semantic Boundary"
        
        if tracker:
            tracker.increment_metric("taxonomy_decisions")
            tracker.log("CLASSIFY", family.value, str(evidence), "TAXONOMY", "PASS")
        
        return TaxonomicDecision(
            family=family,
            structural_basis=evidence,
            satisfied_criteria=tuple(satisfied_criteria),
            unsatisfied_criteria=tuple(unsatisfied_criteria),
            contradictory_criteria=tuple(contradictory_criteria),
            composition_status=composition_status,
            classification_provenance=provenance
        )
