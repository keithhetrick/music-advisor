"""
Helper utilities to parse helper text or JSON payloads into dicts for the host.
"""

from __future__ import annotations

import json
from typing import Any, Dict


class ParseError(Exception):
    pass


def _extract_json_after_marker(text: str, marker: str = "/audio import") -> str:
    idx = text.find(marker)
    if idx == -1:
        raise ParseError("No '/audio import' marker found in helper text.")
    brace_idx = text.find("{", idx)
    if brace_idx == -1:
        raise ParseError("No JSON object found after '/audio import' marker.")
    snippet = text[brace_idx:]
    # naive brace balancing to extract first object
    depth = 0
    for i, ch in enumerate(snippet):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return snippet[: i + 1]
    raise ParseError("Unbalanced JSON braces after '/audio import'.")


def parse_helper_text(text: str) -> Dict[str, Any]:
    """
    Accepts helper text that contains `/audio import { ... }` and returns a dict.
    """
    try:
        json_str = _extract_json_after_marker(text)
        return json.loads(json_str)
    except ParseError:
        # If marker not found, try raw JSON parse as fallback.
        try:
            return json.loads(text)
        except Exception as exc:  # noqa: BLE001
            raise ParseError(f"Unable to parse helper text: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ParseError(f"Malformed JSON in helper text: {exc}") from exc


def parse_payload(obj: Any) -> Dict[str, Any]:
    """
    Ensure the incoming object is a dict (from JSON load or other source).
    """
    if isinstance(obj, dict):
        return obj
    raise ParseError("Payload must be a JSON object.")

__all__ = ["parse_helper_text", "parse_payload", "ParseError"]
