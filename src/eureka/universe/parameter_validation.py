"""
Utility module for validating human‑submitted parameter changes against an allowed contract.
The contract is derived from the problem model (if it defines a `parameters` field) or
falls back to an empty list, meaning no parameters are permitted.
"""

from typing import Dict, List


def get_allowed_parameters(canonical) -> List[str]:
    """Return a list of permitted parameter names for the current work.

    The function looks for a `parameters` attribute on the problem model. The
    attribute is expected to be a mapping from name to definition. If the
    attribute does not exist, an empty list is returned, which effectively denies
    all parameter changes.
    """
    problem = getattr(canonical, "problem", None)
    if problem is None:
        return []
    params = getattr(problem, "parameters", None)
    if isinstance(params, dict):
        return list(params.keys())
    return []


def is_parameter_change_allowed(canonical, changes: Dict) -> bool:
    """Validate that *all* keys in ``changes`` are allowed.

    Returns ``True`` if every key is present in the allowed‑parameter list.
    ``False`` otherwise.
    """
    allowed = set(get_allowed_parameters(canonical))
    return all(key in allowed for key in changes.keys())
