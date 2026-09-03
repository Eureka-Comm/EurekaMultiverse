"""Append-only, versioned ledger for the evolution loop.

Every proposal and every measured outcome is a separate record appended to a
JSON-lines file. Versions are monotic (v1, v2, ...) and are assigned by the
ledger, so nothing is ever overwritten: history is the ground truth that lets
us state with evidence that the system *evolved*, not merely changed.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .proposal import EvolutionProposal, ProposalStatus

RECORD_PROPOSAL = "PROPOSAL"
RECORD_OUTCOME = "OUTCOME"
RECORD_STATUS = "STATUS"


class EvolutionLedger:
    def __init__(self, path: str = "data/evolution/ledger.ndjson"):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    # ---- low-level io ---------------------------------------------------- #
    def _read_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        records: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    def _append(self, record: Dict[str, Any]) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ---- versioning ------------------------------------------------------ #
    def proposals(self) -> List[Dict[str, Any]]:
        return [r for r in self._read_all() if r.get("record") == RECORD_PROPOSAL]

    def last_version(self) -> Optional[str]:
        versions = [
            int(p["version"].lstrip("v"))
            for p in self.proposals()
            if str(p.get("version", "")).lstrip("v").isdigit()
        ]
        return f"v{max(versions)}" if versions else None

    def next_version(self) -> str:
        cur = self.last_version()
        n = int(cur.lstrip("v")) + 1 if cur else 1
        return f"v{n}"

    # ---- writes ---------------------------------------------------------- #
    def register(self, proposal: EvolutionProposal) -> Dict[str, Any]:
        """Append a proposal record, assigning the next version."""
        # Assign the canonical version (overrides anything the reasoner guessed).
        proposal.version = self.next_version()
        proposal.stamp()
        proposal.status = ProposalStatus.PENDING
        record = {
            "record": RECORD_PROPOSAL,
            "version": proposal.version,
            "propuesta_id": proposal.propuesta_id,
            "created_at": proposal.created_at,
            "status": proposal.status.value,
            "proposal": proposal.model_dump(mode="json"),
        }
        self._append(record)
        return record

    def set_status(self, version: str, status: ProposalStatus, note: str = "") -> Dict[str, Any]:
        record = {
            "record": RECORD_STATUS,
            "version": version,
            "status": status.value,
            "at": datetime.now().isoformat(timespec="seconds"),
            "note": note,
        }
        self._append(record)
        return record

    def record_outcome(self, version: str, metrics: Dict[str, Any], note: str = "") -> Dict[str, Any]:
        record = {
            "record": RECORD_OUTCOME,
            "version": version,
            "metrics": metrics,
            "at": datetime.now().isoformat(timespec="seconds"),
            "note": note,
        }
        self._append(record)
        return record

    # ---- reads ----------------------------------------------------------- #
    def history(self) -> List[Dict[str, Any]]:
        return self._read_all()

    def get(self, version: str) -> Optional[Dict[str, Any]]:
        return next((p for p in self.proposals() if p.get("version") == version), None)

    def outcomes(self, version: str) -> List[Dict[str, Any]]:
        return [r for r in self._read_all() if r.get("record") == RECORD_OUTCOME and r.get("version") == version]

    def status_of(self, version: str) -> Optional[str]:
        """Effective status = last STATUS record for the version, else the proposal's own."""
        proposal = self.get(version)
        if proposal is None:
            return None
        status_recs = [
            r for r in self._read_all()
            if r.get("record") == RECORD_STATUS and r.get("version") == version
        ]
        return status_recs[-1]["status"] if status_recs else proposal.get("status")

    def pending(self) -> List[Dict[str, Any]]:
        out = []
        for p in self.proposals():
            if self.status_of(p["version"]) == ProposalStatus.PENDING.value:
                out.append(p)
        return out
