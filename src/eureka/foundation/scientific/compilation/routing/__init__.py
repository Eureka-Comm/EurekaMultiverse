"""
EUREKA Semantic Compilation Boundary Architecture

This package provides the classification, taxonomy, routing, and admission gates
required to process mathematical formulas before they reach any physical compiler.

Provenance: Phase 12 & 13
"""
from .taxonomy import TaxonomicFamily, RoutingState, StructuralEvidence, TaxonomicDecision
from .classifier import Classifier
from .exceptions import EUREKAArchitecturalException, ArchitecturalRoutingRejection, UnresolvedTaxonomyError, AdmissionRejection
from .provenance import TopologicalTracker, ProvenanceRecord
from .router import Router, RoutingDecision
from .admission import PrimitiveAdmissionGate, DerivedAdmissionGate
