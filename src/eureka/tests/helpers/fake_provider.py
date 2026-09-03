# -*- coding: utf-8 -*-
"""Fake CognitiveProvider implementation for unit tests.

The provider returns deterministic proposals and can be configured to simulate
different failure modes.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from ..universe.cognitive_provider import (
    CognitiveProvider,
    ProviderResult,
    ProviderMetadata,
    AgentDefinition,
)


class FakeProvider(CognitiveProvider):
    """A deterministic in‑memory provider used for testing.

    Parameters
    ----------
    mode: str, optional
        Determines the behavior of ``generate``. Supported values:
        ``"success"`` – returns ``ProviderResult.SUCCESS`` with a deterministic
        proposal.
        ``"timeout"`` – simulates a timeout, returns ``ProviderResult.TIMEOUT``.
        ``"unavailable"`` – simulates a connection failure, returns
        ``ProviderResult.UNAVAILABLE``.
        ``"invalid"`` – simulates malformed JSON, returns
        ``ProviderResult.INVALID_RESPONSE``.
        ``"fail"`` – simulates a provider‑side fatal error, returns
        ``ProviderResult.FAIL_CLOSED``.
    """

    def __init__(self, mode: str = "success") -> None:
        if mode not in {"success", "timeout", "unavailable", "invalid", "fail"}:
            raise ValueError(f"Unsupported mode: {mode}")
        self.mode = mode
        self.last_proposal: Dict[str, Any] | None = None

    def _deterministic_payload(self) -> Dict[str, Any]:
        """Return a simple deterministic payload used in the success case."""
        return {"example": "deterministic"}

    def generate(
        self,
        agent_def: AgentDefinition,
        payload: dict,
        context: dict,
    ) -> ProviderResult:
        # Compute metadata (not used by tests but part of contract)
        request_id = str(uuid.uuid4())
        metadata = ProviderMetadata(
            provider=self.__class__.__name__,
            model=agent_def.model,
            agent_id=str(uuid.uuid4()),
            agent_version="1.0",
            request_id=request_id,
            input_hash=ProviderMetadata.compute_hash(payload),
            output_hash="",
        )
        # Store metadata hash of output later if needed
        if self.mode == "success":
            proposal = {
                "type": "typed_proposal",
                "content": "deterministic proposal",
                "metadata": metadata.dict(),
            }
            self.last_proposal = proposal
            # Compute output hash now
            metadata.output_hash = ProviderMetadata.compute_hash(proposal)
            return ProviderResult.SUCCESS
        elif self.mode == "timeout":
            return ProviderResult.TIMEOUT
        elif self.mode == "unavailable":
            return ProviderResult.UNAVAILABLE
        elif self.mode == "invalid":
            return ProviderResult.INVALID_RESPONSE
        elif self.mode == "fail":
            return ProviderResult.FAIL_CLOSED
        # Fallback (should never reach)
        return ProviderResult.FAIL_CLOSED
