"""
Minimal rule-based intent classifier for chat/reco flows.
Keeps logic modular and safe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Intent = Literal[
    "tempo",
    "key",
    "neighbors",
    "hci",
    "ttc",
    "qa",
    "status",
    "artifacts",
    "metadata",
    "lane_summary",
    "key_targets",
    "tempo_targets",
    "compare",
    "why",
    "help",
    "legend",
    "context",
    "unknown",
]


@dataclass
class IntentResult:
    intent: Intent
    text: str


def classify_intent(text: str, intent_model=None) -> IntentResult:
    txt = (text or "").lower()
    # Optional model hook
    if callable(intent_model):
        try:
            predicted = intent_model(txt)
            if predicted in Intent.__args__:  # type: ignore[attr-defined]
                return IntentResult(predicted, text)
        except Exception:
            pass
    # Fast matches
    if any(tok in txt for tok in ("tempo", "bpm", "speed")):
        return IntentResult("tempo", text)
    if "key" in txt:
        return IntentResult("key", text)
    if "neighbor" in txt or "similar" in txt or "nearest" in txt:
        return IntentResult("neighbors", text)
    if "hci" in txt or "echo" in txt or "historical" in txt:
        return IntentResult("hci", text)
    if "ttc" in txt:
        return IntentResult("ttc", text)
    if "qa" in txt or "clipping" in txt or "silence" in txt or "quality" in txt:
        return IntentResult("qa", text)
    if re.search(r"status|health", txt):
        return IntentResult("status", text)
    if "artifact" in txt or "files" in txt or "available" in txt:
        return IntentResult("artifacts", text)
    if "metadata" in txt or "audio info" in txt:
        return IntentResult("metadata", text)
    if "lane summary" in txt or "lane overview" in txt:
        return IntentResult("lane_summary", text)
    if "key target" in txt:
        return IntentResult("key_targets", text)
    if "tempo target" in txt or "tempo nudge" in txt:
        return IntentResult("tempo_targets", text)
    if "why" in txt or "rationale" in txt:
        return IntentResult("why", text)
    if "compare" in txt or "reverse engineer" in txt or "reverse-engineer" in txt:
        return IntentResult("compare", text)
    if "help" in txt:
        return IntentResult("help", text)
    if "legend" in txt or "what does st" in txt:
        return IntentResult("legend", text)
    if "context" in txt:
        return IntentResult("context", text)
    # Lightweight keyword scoring fallback
    keyword_map = {
        "tempo": ["tempo", "bpm", "speed"],
        "key": ["key", "tonality", "mode"],
        "neighbors": ["neighbor", "similar", "nearest", "echo"],
        "hci": ["hci", "historical", "echo"],
        "ttc": ["ttc", "time to chorus"],
        "qa": ["qa", "clipping", "silence", "quality"],
        "status": ["status", "health"],
        "artifacts": ["artifacts", "files", "available"],
    }
    scores = {k: 0 for k in keyword_map}
    for intent_name, words in keyword_map.items():
        for w in words:
            if w in txt:
                scores[intent_name] += 1
    best_intent = max(scores, key=scores.get)
    if scores.get(best_intent, 0) > 0:
        return IntentResult(best_intent, text)
    return IntentResult("unknown", text)


__all__ = ["classify_intent", "IntentResult", "Intent"]
