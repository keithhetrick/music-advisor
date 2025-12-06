"""
Static tutorials/help content for the host layer.
Deterministic and safe to serve without external dependencies.
"""
from __future__ import annotations

from typing import Any, Dict, List

TUTORIALS: Dict[str, Dict[str, Any]] = {
    "getting_started": {
        "title": "Getting Started",
        "steps": [
            "Provide an /audio payload (helper text or JSON).",
            "Optionally pass a market_norms snapshot to enable norm-aware advice.",
            "Ask about tempo/groove/loudness/mood, or 'plan' if advisor_sections exist.",
            "Use 'more' to page through detailed slices.",
            "Use 'compare' after a new payload to see what changed.",
        ],
        "tips": [
            "HCI is descriptive, not predictive.",
            "Check ui_hints.quick_actions for suggested follow-ups.",
        ],
    },
    "future_back": {
        "title": "Future-Back Mode",
        "steps": [
            "Include advisor_target.mode = future_back in the payload.",
            "Host exposes CURRENT_POSITION, DESTINATION, GAP_MAP, REVERSE_ENGINEERED_ACTIONS, and PHILOSOPHY_REMINDER.",
            "Ask 'plan' to see these sections; use 'more' to page.",
        ],
        "tips": [
            "Respect constraints (keep_mood, keep_tempo_range) when interpreting the plan.",
        ],
    },
    "compare": {
        "title": "Compare Versions",
        "steps": [
            "Analyze a payload; then analyze a new version.",
            "Use 'compare' intent to see HCI/band/axes changes.",
        ],
        "tips": [
            "Only diffs what exists in both recommendations.",
        ],
    },
}


def tutorial_list() -> List[Dict[str, str]]:
    return [{"id": k, "title": v["title"]} for k, v in TUTORIALS.items()]


def get_tutorial(topic: str) -> Dict[str, Any]:
    return TUTORIALS.get(topic) or TUTORIALS.get("getting_started", {})


__all__ = ["get_tutorial", "tutorial_list", "TUTORIALS"]
