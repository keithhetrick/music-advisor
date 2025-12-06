"""
Shared helpers for fetching and shaping AcousticBrainz data.

Designed to keep the AcousticBrainz integration compact and Tier 3 only.
"""
from __future__ import annotations

import json
from statistics import mean
from typing import Any, Dict, Optional


def _get_nested(obj: Dict[str, Any], *path: str) -> Any:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _safe_float(val: Any) -> Optional[float]:
    try:
        if val is None:
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _pick_highlevel_prob(highlevel_root: Dict[str, Any], name: str, label: str | None = None) -> Optional[float]:
    """
    AcousticBrainz highlevel blocks often look like:
      { "value": "danceable", "probability": 0.82, "all": { "danceable": 0.82, ... } }
    Grab either the probability or a label-specific prob from "all".
    """
    block = highlevel_root.get(name) if isinstance(highlevel_root, dict) else None
    if not isinstance(block, dict):
        return None

    if label and isinstance(block.get("all"), dict):
        prob = _safe_float(block["all"].get(label))
        if prob is not None:
            return prob

    prob = _safe_float(block.get("probability"))
    if prob is not None:
        return prob

    return None


def extract_compact_features(low_json: Dict[str, Any] | None, high_json: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Reduce AcousticBrainz low/high level JSON into a small scalar subset.
    This keeps the DB light while preserving the fields needed for fallback.
    """
    low = low_json or {}
    high_root = (high_json or {}).get("highlevel") or (high_json or {})

    compact: Dict[str, Any] = {}

    tempo = _safe_float(_get_nested(low, "rhythm", "bpm") or _get_nested(low, "tempo", "bpm"))
    if tempo is not None:
        compact["tempo_bpm"] = tempo

    loudness = _safe_float(
        _get_nested(low, "lowlevel", "average_loudness")
        or _get_nested(low, "tonal", "average_loudness")
        or _get_nested(low, "metadata", "audio_properties", "replaygain_track_gain")
    )
    if loudness is not None:
        compact["average_loudness"] = loudness

    onset_rate = _safe_float(_get_nested(low, "rhythm", "onset_rate"))
    if onset_rate is not None:
        compact["onset_rate"] = onset_rate

    dyn_complexity = _safe_float(_get_nested(low, "lowlevel", "dynamic_complexity"))
    if dyn_complexity is not None:
        compact["dynamic_complexity"] = dyn_complexity

    key_key = _get_nested(low, "tonal", "key_key")
    if isinstance(key_key, str):
        compact["key_key"] = key_key
    key_scale = _get_nested(low, "tonal", "key_scale")
    if isinstance(key_scale, str):
        compact["key_scale"] = key_scale

    mfcc_mean = _get_nested(low, "lowlevel", "mfcc", "mean")
    if isinstance(mfcc_mean, (list, tuple)) and mfcc_mean:
        compact["mfcc_mean_first3"] = [round(float(x), 6) for x in mfcc_mean[:3]]

    # Highlevel probabilities used as proxies for energy/valence
    for name, label in [
        ("danceability", "danceable"),
        ("mood_acoustic", "acoustic"),
        ("mood_aggressive", "aggressive"),
        ("mood_electronic", "electronic"),
        ("mood_happy", "happy"),
        ("mood_party", "party"),
        ("mood_relaxed", "relaxed"),
        ("mood_sad", "sad"),
    ]:
        prob = _pick_highlevel_prob(high_root, name, label)
        if prob is not None:
            compact[name] = prob

    return compact


def compact_to_probe_axes(compact: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Map compact AcousticBrainz features onto the echo probe axes.
    Returns None if required fields are missing.
    """
    tempo = _safe_float(compact.get("tempo_bpm"))
    loudness = _safe_float(compact.get("average_loudness"))

    energy_vals = []
    for key in ("danceability", "mood_aggressive", "mood_electronic", "mood_party"):
        val = _safe_float(compact.get(key))
        if val is not None:
            energy_vals.append(val)
    energy = mean(energy_vals) if energy_vals else None

    happy = _safe_float(compact.get("mood_happy"))
    sad = _safe_float(compact.get("mood_sad"))
    relaxed = _safe_float(compact.get("mood_relaxed"))
    v_list: list[float] = []
    if happy is not None or sad is not None:
        h = happy if happy is not None else 0.5
        s = sad if sad is not None else 0.5
        v_list.append(0.5 + (h - s))
    if relaxed is not None:
        v_list.append(relaxed)
    valence = mean(v_list) if v_list else None

    if None in (tempo, energy, valence, loudness):
        return None

    # Clamp valence to [0, 1] to avoid pathological values from proxies
    valence = max(0.0, min(1.0, float(valence)))

    return {
        "tempo": float(tempo),
        "energy": float(energy),
        "valence": float(valence),
        "loudness": float(loudness),
    }


def load_compact_from_json(json_text: str | bytes | bytearray) -> Dict[str, Any]:
    return json.loads(json_text)
