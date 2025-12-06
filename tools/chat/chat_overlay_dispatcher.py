"""
Chat-facing dispatcher to answer tempo/key overlay questions using sidecars.
Keeps logic modular: no recomputation, uses loaders + chat summaries.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from tools.overlay_sidecar_loader import load_key_overlay_payload, load_tempo_overlay_payload
from tools.chat.overlay_text_helpers import chat_key_summary, chat_tempo_summary, expand_overlay_text


def _short_legend() -> str:
    return "legend: st=semitones, w=weight, c5=circle-of-fifths distance, tags=rationale tags"


def _fmt_tempo_reply(summary: Dict, detail: str = "summary") -> str:
    if not summary:
        return "Tempo overlay not available for this song."
    adv = summary.get("advisory") or {}
    pieces = []
    warnings = []
    if summary.get("lane_profile"):
        pieces.append(f"lane_profile: {summary['lane_profile']}")
    hot = summary.get("hot_zone")
    if hot:
        pieces.append(f"hot_zone: {hot[0]:.1f}–{hot[1]:.1f} BPM")
    peak = summary.get("primary_peak") or {}
    if peak:
        pieces.append(f"primary_peak: {peak.get('min_bpm'):.1f}–{peak.get('max_bpm'):.1f} BPM (~{(peak.get('weight') or 0)*100:.1f}% lane)")
    shape = summary.get("shape") or {}
    if shape:
        pieces.append(f"shape: skew={shape.get('skew',0):.2f}, kurtosis={shape.get('kurtosis',0):.2f}")
    if summary.get("neighbor_bins") and detail == "verbose":
        pieces.append(f"neighbors: {summary.get('neighbor_bins')}")
    if summary.get("warning"):
        warnings.append(summary["warning"])
    text = adv.get("text")
    if text:
        pieces.append(f"advisory: {text}")
    out = " | ".join(pieces) if pieces else "Tempo overlay not available."
    if warnings and detail == "verbose":
        out += f" | warnings: {', '.join(warnings)}"
    return out


def _fmt_key_reply(summary: Dict, detail: str = "summary") -> str:
    if not summary:
        return "Key overlay not available for this song."
    adv = summary.get("advisory") or {}
    pieces = []
    warnings = []
    shape = summary.get("lane_shape") or {}
    if shape:
        maj = shape.get("mode_split", {}).get("major_share", 0)
        minr = shape.get("mode_split", {}).get("minor_share", 0)
        pieces.append(f"lane_shape: entropy={shape.get('entropy',0):.2f}, flatness={shape.get('flatness',0):.2f}, major={maj*100:.1f}%, minor={minr*100:.1f}%")
    if summary.get("mode_top_keys"):
        mt = summary["mode_top_keys"]
        if mt.get("major"):
            pieces.append("top_major: " + ", ".join(mt["major"]))
        if mt.get("minor"):
            pieces.append("top_minor: " + ", ".join(mt["minor"]))
    if summary.get("fifths_chain"):
        pieces.append("fifths_chain: " + ", ".join(summary["fifths_chain"]))
    targets_h = summary.get("target_key_moves_human") or []
    if targets_h:
        pieces.append("targets: " + " | ".join(targets_h))
    if detail == "verbose" and summary.get("target_key_moves"):
        pieces.append(f"targets_raw: {summary.get('target_key_moves')}")
    if summary.get("warning"):
        warnings.append(summary["warning"])
    text = adv.get("text")
    if text:
        pieces.append(f"advisory: {text}")
    pieces.append(_short_legend())
    out = " | ".join(pieces)
    if warnings and detail == "verbose":
        out += f" | warnings: {', '.join(warnings)}"
    return out


def handle_tempo_intent(client_rich: Path, detail: str = "summary") -> str:
    payload = load_tempo_overlay_payload(client_rich)
    if not payload:
        return "Tempo overlay not available for this song."
    summary = chat_tempo_summary(payload, max_neighbors=2)
    return _fmt_tempo_reply(summary, detail=detail)


def handle_key_intent(client_rich: Path, detail: str = "summary") -> str:
    payload = load_key_overlay_payload(client_rich)
    if not payload:
        return "Key overlay not available for this song."
    payload = expand_overlay_text(payload)
    summary = chat_key_summary(payload, max_targets=3)
    return _fmt_key_reply(summary, detail=detail)


def handle_intent(intent: str, client_rich: Path, detail: str = "summary") -> str:
    intent = (intent or "").lower()
    if "tempo" in intent or "bpm" in intent:
        return handle_tempo_intent(client_rich, detail=detail)
    if "key" in intent:
        return handle_key_intent(client_rich, detail=detail)
    return "Unknown intent. Ask about tempo or key overlays."


__all__ = ["handle_tempo_intent", "handle_key_intent", "handle_intent"]
