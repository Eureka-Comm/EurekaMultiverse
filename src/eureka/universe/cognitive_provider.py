# -*- coding: utf-8 -*-
"""cognitive_provider.py

Contract definition for the Cognitive Provider layer.

The provider is a read‑only adapter that receives an immutable payload and
produces a typed proposal.  It must never receive or mutate a
`CanonicalWorkState`, must not perform any I/O, subprocess calls, or
deployment actions.
"""

from __future__ import annotations

import abc
import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Minimal stub for AgentDefinition – the real definition lives elsewhere in the
# system.  We only need it for type checking in the contract.
# ---------------------------------------------------------------------------


class AgentDefinition(BaseModel):
    """A lightweight definition of an agent.

    Only the fields required by the contract are included.  Additional fields
    may be added by the concrete implementation.
    """

    description: str = Field(..., description="Human‑readable description of the agent")
    system_prompt: str = Field(..., description="Prompt that guides the LLM behaviour")
    tools: list[str] = Field(default_factory=list, description="Names of allowed tools")
    model: str = Field(..., description="Identifier of the LLM model to use")


# ---------------------------------------------------------------------------
# ProviderResult – possible outcomes of a provider invocation.
# ---------------------------------------------------------------------------


class ProviderResult(Enum):
    SUCCESS = "SUCCESS"
    UNAVAILABLE = "UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    FAIL_CLOSED = "FAIL_CLOSED"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# ProviderMetadata – immutable provenance information for each call.
# ---------------------------------------------------------------------------


class ProviderMetadata(BaseModel):
    provider: str = Field(..., description="Name of the provider implementation (e.g. 'FakeProvider')")
    model: str = Field(..., description="Underlying LLM model identifier")
    agent_id: str = Field(..., description="Unique identifier for the AgentDefinition instance")
    agent_version: str = Field(..., description="Version string of the agent definition")
    request_id: str = Field(..., description="Unique request identifier (UUID)")
    input_hash: str = Field(..., description="SHA‑256 hash of the canonical JSON payload")
    output_hash: str = Field(..., description="SHA‑256 hash of the provider's raw output (JSON)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the call")

    @staticmethod
    def compute_hash(payload: Dict[str, Any]) -> str:
        """Return a deterministic SHA‑256 hex digest of *payload*.

        The payload is first converted to a canonical JSON string using sorted keys
        and the compact separators mandated by the contract.
        """
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Abstract base class for all providers.
# ---------------------------------------------------------------------------


class CognitiveProvider(abc.ABC):
    """Read‑only provider contract.

    Implementations must **not** accept a mutable ``CanonicalWorkState``; instead
    they receive a serialisable ``payload`` that is derived from the state.
    The method must be pure – no file system writes, no subprocesses, and no
    network calls beyond the LLM provider itself.
    """

    @abc.abstractmethod
    def generate(
        self,
        agent_def: AgentDefinition,
        payload: dict,
        context: dict,
    ) -> ProviderResult:
        """Generate a typed proposal.

        Parameters
        ----------
        agent_def:
            The ``AgentDefinition`` describing the LLM configuration and system
            prompt.
        payload:
            Immutable, JSON‑serialisable representation of the portion of the
            canonical state required by the EM component.
        context:
            Additional contextual information (e.g. request timestamps, runtime
            flags).  Must also be immutable.

        Returns
        -------
        ProviderResult
            One of the enum values indicating success or a specific failure mode.
        """
        raise NotImplementedError
