"""
Intent registry and helpers for host chat routing.
"""
from __future__ import annotations

import os
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001
    yaml = None

IntentHit = Tuple[str, int]


# Canonical intents and their keyword triggers.
DEFAULT_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "summarize": ["summarize", "summary", "overview"],
    "expand": ["expand", "details", "deeper", "more info"],
    "tutorial": ["help", "tutorial", "guide", "how to", "getting started", "onboarding"],
    "health": ["health", "status", "state", "diagnostic"],
    "compare": ["compare", "previous", "diff", "what changed", "change"],
    "structure": ["tempo", "bpm", "runtime", "length", "structure", "form"],
    "groove": ["groove", "dance", "beat", "rhythm", "swing"],
    "loudness": ["loud", "lufs", "volume", "master", "level"],
    "mood": ["mood", "valence", "happy", "sad", "bright", "dark"],
    "historical": ["neighbor", "decade", "echo", "historical"],
    "optimize": ["improve", "optimize", "recommend", "fix", "next steps"],
    "plan": ["plan", "future", "roadmap"],
    "capabilities": [
        "help",
        "what can you do",
        "capabilities",
        "features",
        "what is this",
        "who are you",
        "commands",
        "about",
        "start",
        "how to start",
        "score",
        "grade",
    ],
    "commands": ["commands", "help", "what can you do", "how to"],
    "general": [],
}

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "intents.yml")


def _load_config_intents() -> Dict[str, List[str]]:
    if yaml is None:
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if isinstance(v, list)}
    except Exception:
        return {}
    return {}


CONFIG_INTENT_KEYWORDS = _load_config_intents()
INTENT_KEYWORDS: Dict[str, List[str]] = CONFIG_INTENT_KEYWORDS or DEFAULT_INTENT_KEYWORDS

# Allowed intents for quick_actions to prevent arbitrary injection.
ALLOWED_QUICK_ACTION_INTENTS = {
    "tutorial",
    "commands",
    "health",
    "compare",
    "plan",
    "structure",
    "groove",
    "loudness",
    "mood",
    "historical",
    "optimize",
    "summarize",
    "expand",
}


def detect_intent(message: str) -> str:
    """
    Light-weight intent classifier based on keyword hits with simple typo tolerance.
    Returns the top intent by number of keyword matches; falls back to general.
    """
    m = message.lower()
    hits: List[IntentHit] = []
    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0
        words = m.split()
        all_keywords = list(keywords) + ALIASES.get(intent, [])
        for kw in all_keywords:
            if not kw:
                continue
            if kw in m:
                score += 1
                continue
            # typo tolerance: fuzzy match against individual words
            for w in words:
                if USE_RAPIDFUZZ:
                    sim = rf_ratio(kw, w) / 100.0
                else:
                    sim = SequenceMatcher(None, kw, w).ratio()
                if sim >= 0.8:
                    score += 1
                    break
        hits.append((intent, score))
    # pick highest score; stable order from INTENT_KEYWORDS definition
    hits.sort(key=lambda x: x[1], reverse=True)
    top_intent, score = hits[0]
    if score == 0:
        return "general"
    return top_intent


def sanitize_quick_actions(actions: List[dict]) -> List[dict]:
    """
    Enforce quick_action intent allowlist and shape.
    """
    sanitized: List[dict] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        intent = action.get("intent")
        label = action.get("label")
        if intent not in ALLOWED_QUICK_ACTION_INTENTS or not label:
            continue
        sanitized.append({"label": str(label), "intent": str(intent)})
    return sanitized
ALIASES: Dict[str, List[str]] = {
    "summarize": ["sumamrize", "summery", "summrise"],
    "groove": ["groov", "rhytm", "rhythm"],
    "loudness": ["loudnes", "lufs", "volum"],
    "mood": ["moodd", "valnce", "valance"],
    "capabilities": ["capabilites", "capabilitie", "what can u do"],
}

USE_RAPIDFUZZ = False
try:
    from rapidfuzz.fuzz import ratio as rf_ratio  # type: ignore

    USE_RAPIDFUZZ = True
except Exception:
    USE_RAPIDFUZZ = False
