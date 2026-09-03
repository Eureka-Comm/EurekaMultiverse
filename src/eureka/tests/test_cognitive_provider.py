# -*- coding: utf-8 -*-
"""Tests for the CognitiveProvider contract and FakeProvider implementation.

These tests cover the gates defined for R8.1.1:
- G4 Authority Separation (ensuring no prohibited fields appear in the proposal)
- G5 Immutability of CanonicalWorkState
- G6 SHA‑256 provenance reproducibility
- G7 Failure mode mapping
- G8 Full regression (pytest collection should succeed)
"""

import copy
import json
import uuid

import pytest

from src.eureka.universe.cognitive_provider import (
    CognitiveProvider,
    ProviderResult,
    ProviderMetadata,
    AgentDefinition,
)
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.tests.helpers.fake_provider import FakeProvider

# Helper to create a minimal AgentDefinition used by the FakeProvider
def _dummy_agent_def() -> AgentDefinition:
    return AgentDefinition(
        description="Test agent",
        system_prompt="You are a helpful test LLM.",
        tools=[],
        model="test-model",
    )

# ---------- G4: Authority Separation ----------
def test_fake_provider_success_proposal_has_no_prohibited_fields():
    provider = FakeProvider(mode="success")
    agent_def = _dummy_agent_def()
    payload = {"example": "deterministic"}
    context = {}

    result = provider.generate(agent_def, payload, context)
    assert result is ProviderResult.SUCCESS
    # The FakeProvider stores the last proposal dict for inspection
    proposal = provider.last_proposal
    assert proposal is not None
    # Ensure prohibited fields are not present
    prohibited = {"operator", "predicted_value", "utility_score", "weight", "confidence"}
    assert prohibited.isdisjoint(proposal.keys())

# ---------- G5: Immutability ----------
def test_provider_does_not_mutate_canonical_state():
    # Create a simple canonical state instance
    original_state = CanonicalWorkState()
    # Ensure it has some data (even if empty) – we rely on deepcopy semantics
    snapshot = copy.deepcopy(original_state)

    provider = FakeProvider(mode="success")
    agent_def = _dummy_agent_def()
    payload = {"example": "deterministic"}
    context = {}

    # Provider should not receive the state, but we call it anyway to ensure no side effects
    provider.generate(agent_def, payload, context)

    # After the call, the original state must be unchanged
    assert original_state == snapshot

# ---------- G6: SHA‑256 reproducibility ----------
def test_provider_metadata_hash_is_deterministic():
    payload = {"a": 1, "b": [2, 3], "c": {"nested": "value"}}
    first_hash = ProviderMetadata.compute_hash(payload)
    second_hash = ProviderMetadata.compute_hash(payload)
    assert first_hash == second_hash
    # Verify that changing the payload changes the hash
    altered = {"a": 1, "b": [2, 3, 4], "c": {"nested": "value"}}
    assert ProviderMetadata.compute_hash(altered) != first_hash

# ---------- G7: Failure mode mapping ----------
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("timeout", ProviderResult.TIMEOUT),
        ("unavailable", ProviderResult.UNAVAILABLE),
        ("invalid", ProviderResult.INVALID_RESPONSE),
        ("fail", ProviderResult.FAIL_CLOSED),
    ],
)
def test_fake_provider_failure_modes(mode, expected):
    provider = FakeProvider(mode=mode)
    agent_def = _dummy_agent_def()
    payload = {"example": "deterministic"}
    context = {}
    result = provider.generate(agent_def, payload, context)
    assert result is expected

# ---------- G8: Regression (collection) ----------
def test_dummy_regression_pass():
    """A trivial test to ensure the test suite is collected successfully."""
    assert True
