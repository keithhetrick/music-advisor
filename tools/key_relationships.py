"""
Shared helpers for musical key relationships.

Keep this isolated so relationship tweaks (relative/parallel/fifths) can be
updated without touching sidecar/pipeline formatting code.
"""
from __future__ import annotations

from typing import List, Tuple

PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_CIRCLE_OF_FIFTHS = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]
_CIRCLE_POSITION = {pc: idx for idx, pc in enumerate(_CIRCLE_OF_FIFTHS)}

ENHARMONIC_EQUIV = {
    "C#": "Db",
    "Db": "C#",
    "D#": "Eb",
    "Eb": "D#",
    "F#": "Gb",
    "Gb": "F#",
    "G#": "Ab",
    "Ab": "G#",
    "A#": "Bb",
    "Bb": "A#",
}

RELATIONSHIP_WEIGHTS = {
    "relative": 1.0,
    "parallel": 0.8,
    "fifth": 0.6,
    "historical_hit_medium": 0.5,
}


def transpose_pc(pc: int, semitones: int) -> int:
    return (pc + semitones) % 12


def circle_distance(pc_a: int, pc_b: int) -> int:
    pos_a = _CIRCLE_POSITION.get(pc_a)
    pos_b = _CIRCLE_POSITION.get(pc_b)
    if pos_a is None or pos_b is None:
        return 12
    return abs(pos_a - pos_b)


def root_name_to_pc(name: str) -> int | None:
    """Parse sharp or flat root name to pitch class."""
    if not name:
        return None
    raw = name.strip().replace("♭", "b").replace("♯", "#")
    # Canonicalize case so values like "Eb", "eB", or "eb" all parse.
    if raw:
        raw = raw[0].upper() + raw[1:].lower()
    if raw in PITCH_CLASS_NAMES:
        return PITCH_CLASS_NAMES.index(raw)
    # flats / enharmonic equivalents
    equiv = ENHARMONIC_EQUIV.get(raw)
    if equiv and equiv in PITCH_CLASS_NAMES:
        return PITCH_CLASS_NAMES.index(equiv)
    return None


def preferred_root_name(pc: int, prefer_flat: bool = False) -> str:
    if not prefer_flat:
        return PITCH_CLASS_NAMES[pc % 12]
    sharp = PITCH_CLASS_NAMES[pc % 12]
    flat = ENHARMONIC_EQUIV.get(sharp)
    return flat or sharp


def preferred_key_name(pc: int, mode: str, prefer_flat: bool = False) -> str:
    return f"{preferred_root_name(pc, prefer_flat)}_{mode}"


def relative_key(pc: int, mode: str) -> Tuple[int, str]:
    if mode == "major":
        return transpose_pc(pc, -3), "minor"
    return transpose_pc(pc, 3), "major"


def parallel_key(pc: int, mode: str) -> Tuple[int, str]:
    return pc, "minor" if mode == "major" else "major"


def fifth_neighbors(pc: int, mode: str) -> List[Tuple[int, str]]:
    return [
        (transpose_pc(pc, 7), mode),   # dominant
        (transpose_pc(pc, -7), mode),  # subdominant
    ]


def neighbors_for(pc: int, mode: str, prefer_flat: bool = False) -> dict:
    """
    Precompute neighbor sets with semitone + circle-of-fifths distances and relationship weights.
    """
    rel_pc, rel_mode = relative_key(pc, mode)
    par_pc, par_mode = parallel_key(pc, mode)
    fif = fifth_neighbors(pc, mode)

    def _entry(target_pc: int, target_mode: str, rel: str) -> dict:
        delta = target_pc - pc
        if delta > 6:
            delta -= 12
        if delta < -6:
            delta += 12
        return {
            "key_name": f"{preferred_root_name(target_pc, prefer_flat)}_{target_mode}",
            "pitch_class": target_pc,
            "mode": target_mode,
            "relationship": rel,
            "semitone_delta": delta,
            "circle_distance": circle_distance(pc, target_pc),
            "weight": RELATIONSHIP_WEIGHTS.get(rel, 0.0),
        }

    neighbors = {
        "relative": _entry(rel_pc, rel_mode, "relative"),
        "parallel": _entry(par_pc, par_mode, "parallel"),
        "fifths": [_entry(pc_nb, mode, "fifth") for pc_nb, mode in fif],
    }
    # Flatten all for convenience
    all_entries = [neighbors["relative"], neighbors["parallel"], *neighbors["fifths"]]
    neighbors["all"] = all_entries
    return neighbors


def precompute_neighbors(prefer_flat: bool = False) -> dict:
    """
    Precompute neighbors for all 12 pitch classes in both modes.
    Returns: {(pc, mode): neighbors_for(...)}
    """
    lookup: dict = {}
    for pc in range(12):
        for mode in ("major", "minor"):
            lookup[(pc, mode)] = neighbors_for(pc, mode, prefer_flat=prefer_flat)
    return lookup
