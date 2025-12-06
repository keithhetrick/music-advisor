from __future__ import annotations

from typing import Any, Dict


def validate_engine_response(resp: Dict[str, Any]) -> None:
    """
    Minimal validator to ensure key fields exist in engine responses.
    Raises ValueError on missing keys.
    """
    required_top = ["rec_version", "advisor_mode", "axes", "optimization", "warnings"]
    for key in required_top:
        if key not in resp:
            raise ValueError(f"Engine response missing required field: {key}")
    # ensure axes is a dict, optimization is a list
    if not isinstance(resp.get("axes"), dict):
        raise ValueError("Engine response 'axes' must be a dict")
    if not isinstance(resp.get("optimization"), list):
        raise ValueError("Engine response 'optimization' must be a list")

    # Optional schema hints
    intent_summaries = resp.get("intent_summaries")
    if intent_summaries is not None and not isinstance(intent_summaries, dict):
        raise ValueError("Engine response 'intent_summaries' must be a dict if present")
    market_norms = resp.get("market_norms_used")
    if market_norms is not None and not isinstance(market_norms, dict):
        raise ValueError("Engine response 'market_norms_used' must be a dict if present")
    provenance = resp.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        raise ValueError("Engine response 'provenance' must be a dict if present")
    validation = resp.get("validation")
    if validation is not None and not isinstance(validation, dict):
        raise ValueError("Engine response 'validation' must be a dict if present")


__all__ = ["validate_engine_response"]
