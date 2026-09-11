"""EUREKA 5.1 — Governed HUMAN_RESPONSE sufficiency (HITL -> Evidence Authority contract).

The human is the AUTHORITY over the information they provide. That does NOT mean any non-empty
human text is automatically SUFFICIENT (still less VALIDATED) for any question. This module makes
the distinction explicit and decides it in **Python** — never in the LLM:

    HUMAN_RESPONSE_RECEIVED   !=   HUMAN_RESPONSE_SUFFICIENT   !=   HUMAN_RESPONSE_VALIDATED

Verdicts (deterministic, content-based, auditable):

- ``INVALID``      : nothing usable was received (empty / whitespace / no substantive token).
- ``INSUFFICIENT`` : a real but non-substantive answer — it echoes the question/intent, declines
                     ("no tengo esa información"), or covers NONE of the requested information.
- ``PARTIAL``      : it covers SOME of the requested information dimensions.
- ``SUFFICIENT``   : it is substantive, is NOT an echo, and covers EVERY requested dimension.

Design constraints honoured here:

- ONE deterministic notion of "substantive token", shared with the EM Descriptor grounding gate
  (``descriptor.lexical_overlap`` / ``substantive_tokens``) so the two content criteria cannot diverge.
- The criteria are derived from the STRUCTURE the request already carries
  (``HumanInteractionRequest.required_information`` + ``question``) — not from a fragile literal match.
- No LLM participates in the verdict. No new store, no new authority, no second canonical state:
  the verdict is persisted inside the existing ``HumanInteractionRequest``.
- Deterministic + pure: same inputs -> same verdict (no clock, no network, no randomness except the
  evaluation timestamp recorded for provenance).
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .descriptor import substantive_tokens

# ---------------------------------------------------------------------------------------------
# Governance constants
# ---------------------------------------------------------------------------------------------
SUFFICIENT = "SUFFICIENT"
PARTIAL = "PARTIAL"
INSUFFICIENT = "INSUFFICIENT"
INVALID = "INVALID"

METHOD = "DETERMINISTIC_LEXICAL_COVERAGE_V1"
AUTHORITY = "PYTHON"

# A substantive answer must carry at least this many substantive tokens to be considered SUFFICIENT.
MIN_SUBSTANTIVE_TOKENS = 6
# Coverage threshold per requested dimension (a share of that dimension's substantive tokens).
COVERAGE_TOKEN_RATIO = 0.34
# Similarity at/above which the response is considered an ECHO of the question/intent.
ECHO_JACCARD = 0.70
# Anti-loop budget: the maximum number of BLOCKING INFORMATION requests for one work. When the
# budget is spent, the workflow stays blocked with an explicit condition instead of looping forever
# (and never publishes over information the human did not provide).
MAX_HUMAN_INFORMATION_ATTEMPTS = 3

_DECLINE_RE = re.compile(
    r"(no\s+(tengo|s[eé]|sabr[ií]a|dispongo|cuento|conozco|hay|existe|aplica)"
    r"|no\s+puedo\s+(dar|aportar|proporcionar|facilitar)"
    r"|sin\s+informaci[oó]n|no\s+estoy\s+seguro)",
    re.IGNORECASE,
)


def _iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def normalize_human_value(value: Any) -> str:
    """Deterministic text form of the human response value (dict/list/str -> text).

    A mapping is rendered ``key: value`` per entry (the caller's existing convention) so both the
    KEYS (which may name the requested dimensions) and the VALUES are available as content.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return "\n".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return "\n".join(str(v) for v in value)
    return str(value)


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _is_echo(response_tokens: set, sources: Sequence[str]) -> bool:
    """True when the response adds NO information beyond the question/intent it answers."""
    if not response_tokens:
        return False
    for src in sources:
        src_tokens = substantive_tokens(src)
        if not src_tokens:
            continue
        if response_tokens <= src_tokens:          # nothing new: a verbatim/near-verbatim echo
            return True
        if _jaccard(response_tokens, src_tokens) >= ECHO_JACCARD:
            return True
    return False


def _dimension_covered(dimension: str, response_tokens: set) -> bool:
    """A requested dimension counts as covered when enough of ITS substantive tokens appear."""
    dim_tokens = substantive_tokens(dimension)
    if not dim_tokens:
        # A dimension with no substantive token (e.g. "N/A", "1)") cannot be verified lexically:
        # it is treated as NOT covered so we never claim coverage we cannot demonstrate.
        return False
    need = max(1, int(len(dim_tokens) * COVERAGE_TOKEN_RATIO + 0.999))
    return len(dim_tokens & response_tokens) >= need


def evaluate_human_response(*, response_value: Any,
                            required_information: Optional[Iterable[str]] = None,
                            question: str = "",
                            user_intent: str = "",
                            objective: str = "") -> Dict[str, Any]:
    """Deterministic verdict on the CONTENT of a human response to an INFORMATION request.

    Returns a JSON-native dict persisted on the request (``HumanInteractionRequest.sufficiency``):
    ``status``/``method``/``authority``/``covered``/``missing``/``reasons``/``coverage_ratio``/
    ``substantive_tokens``/``evaluated_at``.
    """
    text = normalize_human_value(response_value)
    dims: List[str] = [str(d) for d in (required_information or []) if str(d).strip()]
    response_tokens = substantive_tokens(text)
    reasons: List[str] = []

    def _result(status: str, covered: List[str], missing: List[str],
                ratio: float, extra_reasons: Optional[List[str]] = None) -> Dict[str, Any]:
        return {
            "status": status,
            "method": METHOD,
            "authority": AUTHORITY,
            "llm_used": False,
            "covered": covered,
            "missing": missing,
            "reasons": reasons + list(extra_reasons or []),
            "coverage_ratio": round(ratio, 4),
            "substantive_tokens": len(response_tokens),
            "evaluated_at": _iso_now(),
        }

    # 1. Nothing usable received.
    if not text.strip():
        return _result(INVALID, [], dims, 0.0, ["EMPTY_RESPONSE"])
    if not response_tokens:
        return _result(INVALID, [], dims, 0.0, ["NO_SUBSTANTIVE_CONTENT"])

    # 2. Structured refusal: real, honest, but not information.
    declined = bool(_DECLINE_RE.search(text))

    # 3. Echo detection (returns the question / the user intent as if it were data).
    echo_sources = [s for s in (question, user_intent, objective) if (s or "").strip()]
    if _is_echo(response_tokens, echo_sources):
        return _result(INSUFFICIENT, [], dims, 0.0, ["ECHO_OF_QUESTION_OR_INTENT"])

    # 4. Coverage of the requested dimensions (the structure the request already carries).
    covered = [d for d in dims if _dimension_covered(d, response_tokens)]
    missing = [d for d in dims if d not in covered]
    ratio = (len(covered) / float(len(dims))) if dims else 1.0

    if declined:
        return _result(INSUFFICIENT, covered, missing, ratio, ["HUMAN_DECLINED_TO_PROVIDE_INFORMATION"])

    if not dims:
        # No structure to check against: fall back to substance (still deterministic).
        if len(response_tokens) >= MIN_SUBSTANTIVE_TOKENS:
            return _result(SUFFICIENT, [], [], 1.0, ["SUBSTANTIVE_RESPONSE_NO_DIMENSIONS_DECLARED"])
        return _result(INSUFFICIENT, [], [], 0.0, ["TOO_SHORT_FOR_AN_INFORMATION_RESPONSE"])

    if not covered:
        return _result(INSUFFICIENT, covered, missing, ratio, ["NO_REQUIRED_INFORMATION_COVERED"])
    if missing:
        return _result(PARTIAL, covered, missing, ratio, ["PARTIAL_COVERAGE_OF_REQUIRED_INFORMATION"])
    if len(response_tokens) < MIN_SUBSTANTIVE_TOKENS:
        return _result(PARTIAL, covered, missing, ratio, ["TOO_SHORT_FOR_REQUIRED_INFORMATION"])
    return _result(SUFFICIENT, covered, missing, ratio, ["COVERED_ALL_REQUIRED_INFORMATION"])


def is_blocking_sufficiency(status: str) -> bool:
    """True when a response verdict must NOT close the information request as resolved."""
    return (status or "").upper() in (INSUFFICIENT, PARTIAL, INVALID)


def count_information_attempts(human_requests: Optional[Iterable[Any]]) -> int:
    """Number of BLOCKING INFORMATION requests already raised for this work (anti-loop counter)."""
    n = 0
    for hr in (human_requests or []):
        if getattr(hr, "type", "") == "INFORMATION" and getattr(hr, "blocking", False):
            n += 1
    return n


def build_followup_question(*, original_question: str, missing: Sequence[str],
                            attempt: int, previous_response: str = "") -> str:
    """Deterministic follow-up question: states WHAT is still missing. Invents nothing.

    The previous response is NOT re-quoted as if it were data; it is only referenced so the human
    understands why the request is repeated.
    """
    missing_list = [str(m) for m in missing if str(m).strip()]
    lines = [
        "La información recibida no es suficiente para responder de forma fundamentada.",
        f"(Intento {attempt}: tu respuesta no cubrió los puntos solicitados.)",
        "",
        "Sigue faltando información sobre:",
    ]
    lines += [f"{i}) {m}" for i, m in enumerate(missing_list, 1)]
    lines += [
        "",
        "Por favor proporciona datos concretos para cada punto (no repitas la pregunta original: "
        "repetir la pregunta no aporta información).",
    ]
    return "\n".join(lines)
