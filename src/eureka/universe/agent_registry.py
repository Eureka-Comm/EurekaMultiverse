"""EUREKA 5.1 — EMERGENT COGNITIVE CLOUD · LOOP 2: AGENT REGISTRY / LIFECYCLE.

`AgentRegistry` is a DERIVED index/service over the Work's canonical agent network
(`CanonicalWorkState.agent_network`). It is **NOT** a persistence authority:

- it holds no store, opens no file, writes nothing: every mutation happens on the in-memory
  `AgentNetworkState` that lives inside the caller's canonical state, and the EXISTING WorkStore
  authority persists it (human decision of 2026-09-12: "no AgentStore/AgentDatabase/AgentStateStore;
  an AgentRegistry may only be a derived index/service").
- `rebuild_from(canonical)` reconstructs the index from persisted canonical state, so the network
  survives a restart without any second source of truth.

Governance encoded here (fail closed):

- CONSTITUTIONAL vs EMERGENT separation: the eight constitutional EM are read-only references
  (`CONSTITUTIONAL_EM`); only EMERGENT agents are registered, and an emergent agent may never take a
  constitutional id.
- Creation/orchestration authority: only `EM Core` may register, retire, supersede or mutate an
  agent's configuration. An agent may advance its OWN execution outcome (RUNNING -> RETURNED/FAILED)
  and nothing else; it can never modify another agent.
- Lifecycle: every transition goes through the single `ALLOWED_TRANSITIONS` table of the contract
  layer (illegal transitions, going backwards, or exceeding a FROZEN agent all fail closed).
- Authority creep: configuration updates are validated with
  `AgentGenome.assert_no_authority_escalation` (identity/ownership/authority/policy are immutable).
- Cross-work isolation: the registry is bound to one work_id/problem_id and rejects any foreign
  genome (no cross-work / cross-problem contamination).
"""
from __future__ import annotations

import datetime
from typing import Dict, List, Optional

from .agent_genome import (CONSTITUTIONAL_EM, AgentContractError, AgentGenome, AgentNetworkState,
                           AgentStatus, EmergentAgentRecord, LifecycleEvent, transition)

#: Actors allowed to act on the emergent network. `EM Core` is the ONLY creation/orchestration
#: authority; "AGENT:<id>" is an agent acting on ITS OWN execution outcome.
CORE_ACTOR = "EM Core"


def agent_actor(agent_id: str) -> str:
    return f"AGENT:{agent_id}"


def _utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class AgentRegistry:
    """Derived index/service over one Work's emergent agent network (no persistence of its own)."""

    def __init__(self, network: AgentNetworkState, *, work_id: str, problem_id: str) -> None:
        if not work_id or not problem_id:
            raise AgentContractError("REGISTRY_SCOPE_REQUIRED", "work_id and problem_id are mandatory")
        self._network = network
        self.work_id = work_id
        self.problem_id = problem_id

    # ----------------------------------------------------------------------------------------- #
    # construction / derivation
    # ----------------------------------------------------------------------------------------- #
    @classmethod
    def rebuild_from(cls, canonical) -> "AgentRegistry":
        """Derive the registry from persisted canonical state (single source of truth)."""
        work_id = getattr(getattr(canonical, "work", None), "work_id", "")
        problem = getattr(canonical, "problem", None)
        problem_id = (getattr(problem, "problem_id", "") or "") if problem is not None else ""
        network = getattr(canonical, "agent_network", None)
        if network is None:
            raise AgentContractError("NO_AGENT_NETWORK", "canonical state has no agent_network container")
        return cls(network, work_id=work_id, problem_id=problem_id or work_id)

    def snapshot(self) -> AgentNetworkState:
        """The container the caller persists through the EXISTING Work authority."""
        return self._network

    # ----------------------------------------------------------------------------------------- #
    # reads
    # ----------------------------------------------------------------------------------------- #
    def resolve(self, agent_id: str) -> EmergentAgentRecord:
        record = self._network.by_id(agent_id)
        if record is None:
            raise AgentContractError("AGENT_NOT_FOUND", agent_id)
        return record

    def get(self, agent_id: str) -> Optional[EmergentAgentRecord]:
        return self._network.by_id(agent_id)

    def list(self, *, kind: str = "EMERGENT", status: Optional[AgentStatus] = None,
             work_id: Optional[str] = None) -> List[EmergentAgentRecord]:
        """List agents. `kind`: EMERGENT (default) | CONSTITUTIONAL (references) | ALL."""
        kind_norm = (kind or "EMERGENT").strip().upper()
        if kind_norm == "CONSTITUTIONAL":
            return []
        records = list(self._network.records)
        if work_id:
            records = [r for r in records if r.work_id == work_id]
        if status is not None:
            records = [r for r in records if r.status is status]
        return records

    def constitutional_agents(self) -> List[Dict[str, str]]:
        """Read-only references to the permanent nucleus (never registered, never owned here)."""
        return [{"agent_id": em, "kind": "CONSTITUTIONAL", "owner": em} for em in CONSTITUTIONAL_EM]

    def count(self) -> int:
        return len(self._network.records)

    # ----------------------------------------------------------------------------------------- #
    # guards
    # ----------------------------------------------------------------------------------------- #
    def _assert_actor(self, actor: str, allowed: List[str], *, operation: str) -> None:
        if actor not in allowed:
            raise AgentContractError("UNAUTHORIZED_ACTOR",
                                     f"actor '{actor}' may not perform {operation}")

    def _assert_not_constitutional_id(self, agent_id: str) -> None:
        if agent_id in CONSTITUTIONAL_EM:
            raise AgentContractError("CONSTITUTIONAL_IMPERSONATION", agent_id)

    def _assert_bound_scope(self, genome: AgentGenome) -> None:
        genome.assert_same_work(self.work_id, self.problem_id)

    # ----------------------------------------------------------------------------------------- #
    # create / retire / supersede  (EM Core only)
    # ----------------------------------------------------------------------------------------- #
    def register(self, genome: AgentGenome, *, actor: str = CORE_ACTOR, reason: str = "") -> EmergentAgentRecord:
        """Register a new EMERGENT agent (creation is authorized by EM Core, never by the agent)."""
        self._assert_actor(actor, [CORE_ACTOR], operation="register")
        self._assert_not_constitutional_id(genome.agent_id)
        self._assert_bound_scope(genome)

        existing = self._network.by_id(genome.agent_id)
        if existing is not None:
            # Identity must mean ONE agent: identical content -> idempotent REUSE; different content
            # with the same id -> DUPLICATE (the necessity test must REUSE/MERGE, not duplicate).
            if existing.genome.hash() == genome.hash():
                return existing
            raise AgentContractError("DUPLICATE_AGENT", genome.agent_id)

        record = EmergentAgentRecord(
            genome=genome, status=AgentStatus.CREATED,
            provenance=[f"registered by {actor}", *(genome.provenance or [])],
            history=[LifecycleEvent(from_status=AgentStatus.PROPOSED, to_status=AgentStatus.CREATED,
                                    actor=actor, reason=reason or "Core-authorized creation")])
        self._network.records.append(record)
        return record

    def retire(self, agent_id: str, *, actor: str = CORE_ACTOR, reason: str = "") -> EmergentAgentRecord:
        return self.advance(agent_id, AgentStatus.RETIRED, actor=actor, reason=reason)

    def supersede(self, agent_id: str, new_genome: AgentGenome, *, actor: str = CORE_ACTOR,
                  reason: str = "") -> EmergentAgentRecord:
        """Retire the old agent and register its successor (revision creates successor artifacts)."""
        self._assert_actor(actor, [CORE_ACTOR], operation="supersede")
        old = self.resolve(agent_id)
        if new_genome.agent_id == agent_id:
            raise AgentContractError("SUPERSEDE_REQUIRES_NEW_IDENTITY", agent_id)
        new_genome.assert_same_work(self.work_id, self.problem_id)
        if old.status is not AgentStatus.RETIRED:
            self.advance(agent_id, AgentStatus.RETIRED, actor=actor,
                         reason=reason or f"superseded by {new_genome.agent_id}")
        replacement = self.register(new_genome, actor=actor, reason=reason or f"supersedes {agent_id}")
        replacement.supersedes = agent_id
        old.superseded_by = new_genome.agent_id
        old.updated_at = replacement.updated_at = _utc_iso()
        return replacement

    # ----------------------------------------------------------------------------------------- #
    # lifecycle
    # ----------------------------------------------------------------------------------------- #
    def advance(self, agent_id: str, new_status: AgentStatus, *, actor: str, reason: str = ""
                ) -> EmergentAgentRecord:
        """The ONLY way to move an agent's lifecycle (enforces the single transitions table)."""
        record = self.resolve(agent_id)
        allowed = [CORE_ACTOR]
        # An agent may only report the outcome of ITS OWN execution.
        if new_status in (AgentStatus.RETURNED, AgentStatus.FAILED):
            allowed.append(agent_actor(agent_id))
        self._assert_actor(actor, allowed, operation=f"{agent_id} -> {new_status.value}")

        if record.status is AgentStatus.FROZEN:
            if new_status not in (AgentStatus.COMPLETED, AgentStatus.RETIRED):
                raise AgentContractError("FROZEN_AGENT_MUTATION",
                                         f"FROZEN agent may only complete/retire, not {new_status.value}")
            record.assert_frozen_integrity()

        next_status = transition(record.status, new_status)          # raises if illegal
        previous = record.status
        record.status = next_status
        if next_status is AgentStatus.FROZEN:
            # LOOP 6R: new freezes use the SEMANTIC hash (V2) and record its version, so tamper
            # evidence states which semantics produced the stored value (legacy records stay V1).
            record.frozen_genome_hash = record.genome.hash()
            record.frozen_genome_hash_version = record.genome.hash_version()
        record.history.append(LifecycleEvent(from_status=previous, to_status=next_status,
                                             actor=actor, reason=reason))
        record.updated_at = _utc_iso()
        return record

    def activate(self, agent_id: str, *, actor: str = CORE_ACTOR, reason: str = "") -> EmergentAgentRecord:
        return self.advance(agent_id, AgentStatus.RUNNING, actor=actor, reason=reason)

    def pause(self, agent_id: str, *, actor: str = CORE_ACTOR, reason: str = "paused") -> EmergentAgentRecord:
        return self.advance(agent_id, AgentStatus.BLOCKED, actor=actor, reason=reason)

    def complete(self, agent_id: str, *, actor: str = CORE_ACTOR, reason: str = "") -> EmergentAgentRecord:
        return self.advance(agent_id, AgentStatus.COMPLETED, actor=actor, reason=reason)

    def mark_returned(self, agent_id: str, *, actor: str = CORE_ACTOR, reason: str = "") -> EmergentAgentRecord:
        return self.advance(agent_id, AgentStatus.RETURNED, actor=actor, reason=reason)

    def require_validation(self, agent_id: str, *, actor: str = CORE_ACTOR,
                           reason: str = "") -> EmergentAgentRecord:
        return self.advance(agent_id, AgentStatus.VALIDATION_REQUIRED, actor=actor, reason=reason)

    def validate(self, agent_id: str, *, actor: str = CORE_ACTOR, reason: str = "") -> EmergentAgentRecord:
        """Validation is a Python/Core decision — never the agent's own claim."""
        return self.advance(agent_id, AgentStatus.VALIDATED, actor=actor, reason=reason)

    def freeze(self, agent_id: str, *, actor: str = CORE_ACTOR, reason: str = "") -> EmergentAgentRecord:
        return self.advance(agent_id, AgentStatus.FROZEN, actor=actor, reason=reason)

    # ----------------------------------------------------------------------------------------- #
    # configuration updates (EM Core only; authority/ownership immutable; frozen = rejected)
    # ----------------------------------------------------------------------------------------- #
    def update_genome(self, agent_id: str, patch: Dict[str, object], *, actor: str = CORE_ACTOR,
                      reason: str = "") -> EmergentAgentRecord:
        """Governed configuration update. Rejects authority escalation and frozen mutation."""
        self._assert_actor(actor, [CORE_ACTOR], operation="update_genome")
        record = self.resolve(agent_id)
        if record.status is AgentStatus.FROZEN:
            raise AgentContractError("FROZEN_AGENT_MUTATION", agent_id)
        # Scope/identity first, so the SPECIFIC reason codes win over the generic escalation code.
        current = record.genome.model_dump(mode="json")
        if "work_id" in patch and patch["work_id"] != current.get("work_id"):
            raise AgentContractError("CROSS_WORK_CONTAMINATION", str(patch["work_id"]))
        if "problem_id" in patch and patch["problem_id"] != current.get("problem_id"):
            raise AgentContractError("CROSS_PROBLEM_CONTAMINATION", str(patch["problem_id"]))
        if "agent_id" in patch and patch["agent_id"] != current.get("agent_id"):
            raise AgentContractError("IDENTITY_MUTATION", str(patch["agent_id"]))
        if "identity" in patch and patch["identity"] != current.get("identity"):
            raise AgentContractError("IDENTITY_MUTATION", "identity")
        record.genome.assert_no_authority_escalation(patch)          # authority/ownership/policy
        merged = {**current, **patch}
        record.genome = AgentGenome.model_validate(merged)
        record.provenance.append(f"genome updated by {actor}: {sorted(patch)}")
        record.history.append(LifecycleEvent(from_status=record.status, to_status=record.status,
                                             actor=actor, reason=reason or "configuration update"))
        record.updated_at = _utc_iso()
        return record
