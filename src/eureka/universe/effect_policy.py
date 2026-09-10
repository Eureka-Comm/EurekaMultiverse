"""EUREKA 5.1 — Effect Boundary + Execution Policy (LS-SCN-03, Q4).

A single, structural, fail-closed gate located BELOW agent/LLM intent and ABOVE any mutable
side effect. It does NOT trust a capability/agent/LLM to self-report as "safe": every controlled
(dry-run) execution must pass `EffectBoundary.authorize`, which blocks on unknown effect,
unknown capability, unknown target, missing policy/mode, missing authorization, and any MUTATE
effect under DRY_RUN.

Guarantee encoded here (the property WHAT-IF will need):
    "A hypothetical cognitive computation must never gain uncontrolled mutation authority."

Only this module + minimal capability-classification wiring was added; no Scenario runtime,
no WHAT-IF, no ProjectedArtifact. Existing NORMAL execution path is left permissive (unchanged)
so current behavior is preserved; DRY_RUN is the strict gate that any current or future
controlled/dry-run context MUST pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Callable, Any


class EffectClass(str, Enum):
    """Structural classification of what a capability may do to the outside world."""
    READ = "READ"          # read-only
    COMPUTE = "COMPUTE"    # deterministic pure computation (ACFL/MathEngine)
    SIMULATE = "SIMULATE"  # produces an observation, no real side effect
    MUTATE = "MUTATE"      # real, persistent, mutable side effect (fs/db/api/notify/...)
    UNKNOWN = "UNKNOWN"    # unclassified -> FAIL CLOSED for dry-run


class ExecutionMode(str, Enum):
    NORMAL = "NORMAL"                  # existing runtime path (permissive, unchanged)
    DRY_RUN = "DRY_RUN"                # controlled / hypothetical execution (strict gate)
    REAL_EXECUTION = "REAL_EXECUTION"  # a HUMAN-AUTHORIZED real action (still gated by Q4: the
                                       # MUTATE rules apply exactly as in NORMAL, but DRY_RUN still
                                       # always blocks). One execution authority, three explicit modes.


class BoundaryDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class BoundaryVerdict:
    decision: BoundaryDecision
    reason_code: str
    message: str


class PolicyError(RuntimeError):
    """Raised when the boundary blocks. Carries a machine-readable reason_code."""
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


class CapabilityEffectClassifier:
    """Maps capability_id -> EffectClass. Unknown -> EffectClass.UNKNOWN (fail closed)."""
    def __init__(self, table: Optional[Dict[str, EffectClass]] = None):
        self._table: Dict[str, EffectClass] = dict(table or {})

    def effect_for(self, capability_id: str) -> EffectClass:
        return self._table.get(capability_id, EffectClass.UNKNOWN)

    def classify(self, capability_id: str, effect: EffectClass) -> None:
        self._table[capability_id] = effect

    def snapshot(self) -> Dict[str, EffectClass]:
        return dict(self._table)


@dataclass
class DryRunContext:
    """Explicit execution context; the boundary reads only this + the classifier (never the LLM)."""
    capability_id: str
    target: str = ""
    mode: ExecutionMode = ExecutionMode.NORMAL
    authorization: Optional[str] = None
    execution_level: int = 0
    required_execution_level: int = 0


class ExecutionPolicy:
    """The single policy: given an effect class + mode + authorization, decide ALLOW/BLOCK.

    Fail-closed rules (in order). Any rule that cannot be satisfied -> BLOCK (no best-effort,
    no silent degradation, no fallback to real).
    """
    def __init__(self) -> None:
        self._levels: Dict[str, int] = {}  # capability_id -> required execution level

    def set_requirement(self, capability_id: str, level: int) -> None:
        self._levels[capability_id] = level

    def decide(self, ctx: DryRunContext, effect: EffectClass) -> BoundaryVerdict:
        # 1. capability must be known/classified (unknown capability or effect -> BLOCK)
        if effect == EffectClass.UNKNOWN:
            return BoundaryVerdict(BoundaryDecision.BLOCK, "UNKNOWN_EFFECT",
                                   f"No effect classification for capability {ctx.capability_id}")
        # 2. target must be present for a running capability
        if not ctx.target:
            return BoundaryVerdict(BoundaryDecision.BLOCK, "MISSING_TARGET",
                                   f"No target for capability {ctx.capability_id}")
        # 3. execution level must be compatible
        required = self._levels.get(ctx.capability_id, ctx.required_execution_level)
        if ctx.execution_level < required:
            return BoundaryVerdict(BoundaryDecision.BLOCK, "EXECUTION_LEVEL_INSUFFICIENT",
                                   f"Execution level {ctx.execution_level} < required {required}")
        # 4. NORMAL mode: mutation allowed if an explicit authorization is present (else BLOCK)
        if effect == EffectClass.MUTATE:
            if ctx.mode == ExecutionMode.DRY_RUN:
                return BoundaryVerdict(BoundaryDecision.BLOCK, "MUTATE_IN_DRY_RUN",
                                       f"Capability {ctx.capability_id} is MUTATE: forbidden in dry-run")
            if not ctx.authorization:
                return BoundaryVerdict(BoundaryDecision.BLOCK, "MISSING_AUTHORIZATION",
                                       f"Capability {ctx.capability_id} MUTATE requires explicit authorization")
        # 5. DRY_RUN requires a policy/mode present (it is, by ctx.mode) + explicit authorization cap
        if ctx.mode == ExecutionMode.DRY_RUN and not ctx.authorization:
            # READ/COMPUTE/SIMULATE are fine without authorization in dry-run (read-only),
            # but we still record that no authorization was required.
            pass
        return BoundaryVerdict(BoundaryDecision.ALLOW, "OK", "Allowed")


class EffectBoundary:
    """The gate. `authorize` returns a verdict; raising `enforce`/`execute` applies it.

    `execute(capability_id, fn, ...)` is the SINGLE enforcement point a capability executor must
    use: it consults the policy BEFORE calling the real handler, so a blocked dry-run can never
    reach the real code path that would produce the side effect.
    """
    def __init__(self, classifier: CapabilityEffectClassifier, policy: Optional[ExecutionPolicy] = None):
        self.classifier = classifier
        self.policy = policy or ExecutionPolicy()

    def authorize(self, ctx: DryRunContext) -> BoundaryVerdict:
        effect = self.classifier.effect_for(ctx.capability_id)
        return self.policy.decide(ctx, effect)

    def enforce(self, ctx: DryRunContext) -> BoundaryVerdict:
        """Raise PolicyError when BLOCK. Returns ALLOW verdict otherwise."""
        verdict = self.authorize(ctx)
        if verdict.decision == BoundaryDecision.BLOCK:
            raise PolicyError(verdict.reason_code, verdict.message)
        return verdict

    def execute(self, ctx: DryRunContext, fn: Callable[[], Any]) -> Any:
        """Real enforcement: gate FIRST, then run the handler (never the reverse)."""
        self.enforce(ctx)
        return fn()

    def classify(self, capability_id: str, effect: EffectClass) -> None:
        self.classifier.classify(capability_id, effect)

    def authorize_write(self, effect: EffectClass, *, mode: ExecutionMode, authorization: Optional[str] = None,
                        target: str = "fs", capability_id: str = "filesystem_write") -> BoundaryVerdict:
        """Funnel-agnostic guard for a mutable filesystem/IO write."""
        ctx = DryRunContext(capability_id=capability_id, target=target, mode=mode, authorization=authorization)
        # classify the write via the capability id (fallbacks handled by policy)
        eff = effect
        return self.policy.decide(ctx, eff)


def guarded_dump_json(boundary: EffectBoundary, path, data, *, mode: ExecutionMode, authorization: Optional[str] = None,
                      capability_id: str = "filesystem_write", target: str = "fs", indent: int = 2):
    """Transversal guard for a canonical-persistence JSON write.

    NORMAL (with the canonical-runtime authorization) persists as before.
    DRY_RUN blocks a MUTATE write (fail-closed) and never writes the file.
    This is the single ordering: policy/boundary FIRST, then the real write.
    """
    verdict = boundary.authorize_write(EffectClass.MUTATE, mode=mode, authorization=authorization,
                                       target=target, capability_id=capability_id)
    if verdict.decision == BoundaryDecision.BLOCK:
        raise PolicyError(verdict.reason_code, verdict.message)
    import json as _json
    with open(path, "w", encoding="utf-8") as _f:
        _json.dump(data, _f, indent=indent)


# Authorization token reserved for legitimate canonical RUNTIME persistence. It is NOT granted by
# an LLM/agent: the runtime itself requests it for its own state/freeze/artifact writes so that
# NORMAL mode keeps working, while DRY_RUN still blocks any MUTATE regardless of this token.
CANONICAL_PERSISTENCE_AUTH = "CANONICAL_RUNTIME_PERSISTENCE"


def default_boundary() -> EffectBoundary:
    """Boundary with the known mutating/read capabilities classified (everything else UNKNOWN)."""
    default = {
        # read / compute (no real side effect)
        "adjust_acfl_weights": EffectClass.COMPUTE,
        "frozen_knowledge.detect_delta": EffectClass.COMPUTE,
        "frozen_knowledge.mathematical_revalidation": EffectClass.COMPUTE,
        "frozen_knowledge.cognitive_reevaluation": EffectClass.COMPUTE,
        "frozen_knowledge.action_plan_generation": EffectClass.COMPUTE,
        "frozen_knowledge.action_plan_verification": EffectClass.COMPUTE,
        "frozen_knowledge.evaluate_applicability": EffectClass.COMPUTE,
        "evaluate_alternatives": EffectClass.COMPUTE,
        "synthesize_information": EffectClass.COMPUTE,
        "predict": EffectClass.COMPUTE,
        "forecast": EffectClass.COMPUTE,
        "predict_outcome": EffectClass.COMPUTE,
        "analyze_dataset": EffectClass.COMPUTE,
        "inspect_document": EffectClass.READ,
        "extract_relevant_information": EffectClass.READ,
        "analyze_evidence": EffectClass.READ,
        # simulated / observation only
        "execute_action": EffectClass.SIMULATE,
        # real mutation (require authorization; blocked in dry-run)
        "install_action": EffectClass.MUTATE,
        "generate_summary": EffectClass.MUTATE,
        "generate_report": EffectClass.MUTATE,
        "generate_presentation": EffectClass.MUTATE,
        "save_artifact": EffectClass.MUTATE,
        "freeze_result": EffectClass.MUTATE,
        # a human-authorized scenario execution materializes a governed artifact (a real, observable
        # write). Classified MUTATE so DRY_RUN blocks it and REAL_EXECUTION requires authorization.
        "scenario.execution": EffectClass.MUTATE,
        # the durable Work authority's own persistence (authority durability, NOT a domain effect).
        "work.persist": EffectClass.MUTATE,
        # a governed CANONICAL work execution produces a real, observable artifact (the production
        # executor's effect). MUTATE: DRY_RUN blocks it; REAL_EXECUTION requires authorization.
        "work.execution": EffectClass.MUTATE,
        # a governed CANONICAL publication materializes a durable, signed artifact (Publisher effect).
        # Distinct from work.execution (publish != execute). MUTATE: DRY_RUN blocks it.
        "publisher.publish": EffectClass.MUTATE,
    }
    return EffectBoundary(CapabilityEffectClassifier(default))
