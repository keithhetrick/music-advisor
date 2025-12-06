"""
Helpers to humanize shorthand fields for chat/reco rendering.
"""
from __future__ import annotations

from typing import Dict, List


def humanize_target_move(move: Dict) -> str:
    """
    Convert a target_key_moves entry into a short human-readable string.
    """
    key = move.get("target_key", "n/a")
    delta = move.get("semitone_delta", 0)
    pct = move.get("lane_percent")
    weight = move.get("weight")
    c5 = move.get("circle_distance")
    tags = move.get("rationale_tags") or []
    pieces: List[str] = []
    pieces.append(key)
    pieces.append(f"{'+' if delta > 0 else ''}{delta} st")
    if isinstance(pct, (int, float)):
        pieces.append(f"{pct*100:.1f}% lane")
    if isinstance(weight, (int, float)):
        pieces.append(f"w={weight:.2f}")
    if isinstance(c5, (int, float)):
        pieces.append(f"c5={int(c5)}")
    if tags:
        pieces.append("tags=" + ";".join(tags[:3]))
    return " (".join([pieces[0], ", ".join(pieces[1:]) + ")"]) if len(pieces) > 1 else pieces[0]


def expand_abbreviations(text: str) -> str:
    """
    Expand common abbreviations used in overlays for chat contexts.
    """
    text = text.replace(" st", " semitones")
    text = text.replace(" w=", " weight=")
    text = text.replace(" c5=", " circle-of-fifths-distance=")
    return text


def expand_overlay_text(payload: Dict) -> Dict:
    """
    Copy a payload and expand any known abbreviations in advisory text/target moves.
    """
    out = dict(payload)
    adv = dict(out.get("advisory") or {})
    if adv.get("text"):
        adv["text"] = expand_abbreviations(str(adv["text"]))
    out["advisory"] = adv
    moves = out.get("target_key_moves") or out.get("target_moves") or []
    new_moves = []
    for m in moves:
        mc = dict(m)
        if mc.get("chord_fit_hint"):
            mc["chord_fit_hint"] = expand_abbreviations(str(mc["chord_fit_hint"]))
        new_moves.append(mc)
    out["target_key_moves"] = new_moves
    return out


def _truncate_list(items: List[str], max_len: int) -> List[str]:
    if max_len <= 0:
        return []
    if len(items) <= max_len:
        return items
    return items[:max_len] + [f"...(+{len(items)-max_len} more)"]


def chat_tempo_summary(payload: Dict, max_neighbors: int = 2) -> Dict:
    """
    Build a compact chat-facing tempo summary dict from loader payload.
    """
    neighbors = payload.get("neighbor_bins") or []
    neighbors = neighbors[:max_neighbors] if max_neighbors else neighbors
    return {
        "lane_id": payload.get("lane_id"),
        "song_bpm": payload.get("song_bpm"),
        "hot_zone": payload.get("hot_zone"),
        "hit_medium_percentile_band": payload.get("hit_medium_percentile_band"),
        "primary_peak": payload.get("primary_peak"),
        "lane_profile": payload.get("lane_profile"),
        "shape": payload.get("shape"),
        "neighbors": neighbors,
        "advisory": payload.get("advisory"),
        "warning": payload.get("warning"),
    }


def chat_key_summary(payload: Dict, max_targets: int = 3) -> Dict:
    """
    Build a compact chat-facing key summary dict from loader payload.
    """
    targets = payload.get("target_key_moves") or []
    targets = targets[:max_targets] if max_targets else targets
    human_targets = [humanize_target_move(m) for m in targets]
    return {
        "lane_id": payload.get("lane_id"),
        "song_key": payload.get("song_key"),
        "lane_shape": payload.get("lane_shape"),
        "mode_top_keys": payload.get("mode_top_keys"),
        "fifths_chain": _truncate_list(payload.get("fifths_chain") or [], 6),
        "historical_hit_medium": payload.get("historical_hit_medium"),
        "neighbor_keys": payload.get("neighbor_keys"),
        "target_key_moves": targets,
        "target_key_moves_human": _truncate_list(human_targets, max_targets),
        "advisory": payload.get("advisory"),
        "warning": payload.get("warning"),
    }


__all__ = [
    "humanize_target_move",
    "expand_abbreviations",
    "expand_overlay_text",
    "chat_tempo_summary",
    "chat_key_summary",
]
