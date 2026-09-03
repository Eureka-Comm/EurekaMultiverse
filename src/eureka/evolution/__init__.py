"""EUREKA Evolution Harness.

Supervised, multi-layer self-optimization for the EUREKA cognitive engine, run
under a hard human-in-the-loop gate. Every improvement is proposed as a single
versioned variant, waits for explicit human approval, and is only applied +
measured after that approval. Nothing is applied silently.
"""

from .proposal import EvolutionProposal, ProposalStatus
from .ledger import EvolutionLedger
from .hitl_gate import EvolutionHITLGate, GateError
from .fuzzy_engine import FuzzyController, ACFLBridge
from .loop_driver import EvolutionLoop, EvolutionError

__all__ = [
    "EvolutionProposal",
    "ProposalStatus",
    "EvolutionLedger",
    "EvolutionHITLGate",
    "GateError",
    "FuzzyController",
    "ACFLBridge",
    "EvolutionLoop",
    "EvolutionError",
]
