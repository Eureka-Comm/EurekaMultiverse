from dataclasses import dataclass, field
from typing import List

@dataclass
class ProvenanceRecord:
    stage: str
    decision: str
    basis: str
    target: str
    status: str
    
class TopologicalTracker:
    """
    Physical tracker for CLASSIFY -> ROUTE -> ADMIT -> COMPILE.
    Provenance: Phase 12.7.
    """
    def __init__(self):
        self.records: List[ProvenanceRecord] = []
        self.metrics = {
            "classifier_calls": 0,
            "taxonomy_decisions": 0,
            "router_calls": 0,
            "primitive_route": 0,
            "derived_route": 0,
            "primitive_admission": 0,
            "derived_admission": 0,
            "compiler_invocations": 0,
            "fallbacks": 0
        }
        
    def log(self, stage: str, decision: str, basis: str, target: str, status: str):
        self.records.append(ProvenanceRecord(stage, decision, basis, target, status))
        
    def increment_metric(self, metric: str):
        if metric in self.metrics:
            self.metrics[metric] += 1
