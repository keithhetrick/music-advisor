#!/usr/bin/env python3
"""
Key norms / lane overlay sidecar generator.

Intent:
- Input: lane hit keys (from historical_echo.db) + a song key/mode.
- Output: structured JSON sidecar plus advisory labels for downstream overlays.

Canonical representations observed in-repo:
- Song/audio features store key as root name (e.g., "C#", "A") and mode as "major"/"minor".
- Lane/hit datasets in historical_echo.db store Spotify-style pitch classes (0=C..11=B) and
  mode as 1=major, 0=minor. The `echo_tier` column acts as a lane identifier.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env, make_logger  # type: ignore[import-not-found]  # noqa: E402
from ma_audio_engine.adapters.logging_adapter import log_stage_end, log_stage_start  # type: ignore[import-not-found]  # noqa: E402
from ma_config.paths import get_historical_echo_db_path  # type: ignore[import-not-found]  # noqa: E402
from tools import names  # noqa: E402
from tools.key_relationships import (  # noqa: E402
    PITCH_CLASS_NAMES,
    circle_distance,
    fifth_neighbors,
    parallel_key,
    relative_key,
    transpose_pc,
    root_name_to_pc,
    RELATIONSHIP_WEIGHTS,
    neighbors_for,
    precompute_neighbors,
)
try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None

KEY_ANALYSIS_VERSION = "v1.0"


_LANE_TABLES = [
    "spine_master_v1_lanes",
    "spine_master_tier2_modern_lanes_v1",
    "spine_master_tier3_modern_lanes_v1",
]

LANE_ALIASES = {
    "tier1": "EchoTier_1_YearEnd_Top40",
    "tier1_modern": "EchoTier_1_YearEnd_Top40",
    "tier2": "EchoTier_2_YearEnd_Top100_Modern",
    "tier2_modern": "EchoTier_2_YearEnd_Top100_Modern",
    "tier3": "EchoTier_3_YearEnd_Top200_Modern",
    "tier3_modern": "EchoTier_3_YearEnd_Top200_Modern",
}

def _apply_env_overrides(args: argparse.Namespace, defaults: Dict[str, Any]) -> argparse.Namespace:
    """
    Allow env JSON to override defaults when CLI flags are not provided.
    Env: KEY_NORMS_OPTS='{"neighbor_steps":2,"neighbor_decay":0.6,...}'
    CLI takes precedence; env only applies when the arg is still at its default.
    """
    raw = os.getenv("KEY_NORMS_OPTS")
    if not raw:
        return args
    try:
        data = json.loads(raw)
    except Exception:
        return args
    for key, val in data.items():
        if key in defaults and getattr(args, key, None) == defaults[key]:
            setattr(args, key, val)
    return args


@dataclass
class KeyLaneStats:
    lane_id: str
    total_hits: int
    mode_counts: Dict[str, int]
    key_counts: Dict[str, int]
    top_keys: List[Tuple[str, int]]
    primary_family: List[str]


@dataclass
class KeySongPlacement:
    song_key_name: str
    song_mode: str
    same_key_count: int
    same_key_percent: float
    same_mode_percent: float
    neighbor_keys: List[Dict[str, Any]]


@dataclass
class KeyAdvisory:
    advisory_label: str
    advisory_text: str
    suggested_key_family: List[str]
    suggested_transpositions: List[int]


@dataclass
class SongKey:
    root_name: str
    mode: str
    pitch_class: int

    @property
    def full_name(self) -> str:
        return f"{self.root_name} {self.mode}"

    @property
    def key_name(self) -> str:
        return f"{self.root_name}_{self.mode}"


def _normalize_mode(mode_val: Any) -> Optional[str]:
    if mode_val is None:
        return None
    val = str(mode_val).strip().lower()
    if val in ("major", "maj", "1", "true", "major_key"):
        return "major"
    if val in ("minor", "min", "0", "false", "minor_key"):
        return "minor"
    return None


def _normalize_pitch_class(pc_val: Any) -> Optional[int]:
    if pc_val is None:
        return None
    # Allow int/float pitch-class numbers or sharp/flat root strings.
    if isinstance(pc_val, (int, float)):
        try:
            return int(pc_val) % 12
        except Exception:
            return None
    if isinstance(pc_val, str):
        stripped = pc_val.strip()
        if stripped.replace(".", "", 1).isdigit():
            try:
                return int(float(stripped)) % 12
            except Exception:
                pass
        pc = root_name_to_pc(stripped)
        if pc is not None:
            return pc
    return None


def _circle_distance(pc_a: int, pc_b: int) -> int:
    return circle_distance(pc_a, pc_b)


def _relative_key(pc: int, mode: str) -> Tuple[int, str]:
    return relative_key(pc, mode)


def _parallel_key(pc: int, mode: str) -> Tuple[int, str]:
    return parallel_key(pc, mode)


def _fifth_neighbors(pc: int, mode: str) -> List[Tuple[int, str]]:
    return fifth_neighbors(pc, mode)


def format_key_name(key_name: str, prefer_flat: bool = False) -> str:
    if "_" not in key_name:
        return key_name
    root, mode = key_name.split("_", 1)
    pc = _normalize_pitch_class(root)
    root_disp = PITCH_CLASS_NAMES[pc] if pc is not None else root
    if prefer_flat and pc is not None:
        # Use preferred flat name if available
        from tools.key_relationships import preferred_root_name  # local import to avoid cycles
        root_disp = preferred_root_name(pc, prefer_flat=True)
    return f"{root_disp} {mode}"


def _normalize_key_pair(root: Any, mode: Any) -> Optional[SongKey]:
    pc = _normalize_pitch_class(root)
    norm_mode = _normalize_mode(mode)
    if pc is None or norm_mode is None:
        return None
    root_name = PITCH_CLASS_NAMES[pc]
    return SongKey(root_name=root_name, mode=norm_mode, pitch_class=pc)


def _parse_song_key_string(raw: str) -> Optional[SongKey]:
    if not raw:
        return None
    txt = raw.replace("_", " ").replace("-", " ").strip()
    m = re.match(r"^([A-Ga-g][#b]?)\s+(major|minor|maj|min)$", txt, flags=re.IGNORECASE)
    if m:
        return _normalize_key_pair(m.group(1), m.group(2))
    if " " not in txt:
        # Allow compact forms like "C#m" or "Am"
        low = txt.lower()
        if low.endswith("min"):
            return _normalize_key_pair(txt[:-3], "minor")
        if low.endswith("m"):
            return _normalize_key_pair(txt[:-1], "minor")
        return _normalize_key_pair(txt, "major")
    parts = txt.split()
    if len(parts) >= 2:
        return _normalize_key_pair(parts[0], parts[1])
    return None


def _extract_key_mode_from_json(data: Dict[str, Any]) -> Optional[Tuple[Any, Any]]:
    candidates: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        candidates.append(data)
        for key in ("features", "features_full", "feature_pipeline_meta", "metadata"):
            obj = data.get(key)
            if isinstance(obj, dict):
                candidates.append(obj)
    for obj in candidates:
        key_val = obj.get("key")
        mode_val = obj.get("mode")
        if key_val is not None and mode_val is not None:
            return key_val, mode_val
    return None


def resolve_song_key(
    song_key_arg: Optional[str],
    features_path: Optional[Path],
    song_id: str,
    search_dir: Path,
) -> SongKey:
    if song_key_arg:
        parsed = _parse_song_key_string(song_key_arg)
        if parsed:
            return parsed
        raise SystemExit(f"Could not parse --song-key value '{song_key_arg}' (expected forms like 'C# major').")

    candidate_files: List[Path] = []
    if features_path:
        candidate_files.append(features_path)
    # Best-effort discovery inside the output/search directory
    for suffix in (".features.json", ".merged.json", ".client.json"):
        candidate_files.append(search_dir / f"{song_id}{suffix}")

    for path in candidate_files:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        key_mode = _extract_key_mode_from_json(data)
        if key_mode:
            parsed = _normalize_key_pair(key_mode[0], key_mode[1])
            if parsed:
                return parsed
    raise SystemExit("Could not resolve song key/mode. Pass --song-key or provide a features/client JSON with key/mode.")


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def _normalize_lane_id(lane_id: str) -> Tuple[str, Optional[Tuple[int, int]]]:
    lane_clean = lane_id.strip()
    year_range: Optional[Tuple[int, int]] = None
    if lane_clean.startswith("EchoTier_"):
        return lane_clean, None
    tier = None
    label = None
    m = re.match(r"tier(?P<tier>\d+)(?:[_]{1,2}(?P<label>[A-Za-z0-9_]+))?", lane_clean)
    if m:
        tier = int(m.group("tier"))
        label = m.group("label")
    alias_key = lane_clean.lower()
    if label:
        alias_key = f"tier{tier}_{label}".lower() if tier else alias_key
        if re.match(r"^\d{4}_\d{4}$", label):
            try:
                start, end = label.split("_")
                year_range = (int(start), int(end))
            except Exception:
                year_range = None
    if tier and not label:
        alias_key = f"tier{tier}"
    normalized = LANE_ALIASES.get(alias_key)
    if normalized:
        return normalized, year_range
    if tier:
        fallback = LANE_ALIASES.get(f"tier{tier}_modern") or LANE_ALIASES.get(f"tier{tier}")
        if fallback:
            return fallback, year_range
    return lane_clean, year_range


def load_lane_keys(conn: sqlite3.Connection, lane_id: str) -> List[SongKey]:
    normalized_lane, year_range = _normalize_lane_id(lane_id)
    lane_keys: List[SongKey] = []
    for table in _LANE_TABLES:
        if not _table_exists(conn, table):
            continue
        query = f"SELECT key, mode, year FROM {table} WHERE echo_tier=?"
        cur = conn.execute(query, (normalized_lane,))
        for key_val, mode_val, year_val in cur.fetchall():
            if year_range:
                try:
                    year_int = int(year_val)
                except Exception:
                    continue
                if not (year_range[0] <= year_int <= year_range[1]):
                    continue
            parsed = _normalize_key_pair(key_val, mode_val)
            if parsed:
                lane_keys.append(parsed)
    return lane_keys


def compute_lane_stats(lane_id: str, lane_keys: Iterable[SongKey], top_k: int = 3) -> KeyLaneStats:
    key_counts: Dict[str, int] = {}
    mode_counts: Dict[str, int] = {}
    for lk in lane_keys:
        key_counts[lk.key_name] = key_counts.get(lk.key_name, 0) + 1
        mode_counts[lk.mode] = mode_counts.get(lk.mode, 0) + 1
    total_hits = sum(key_counts.values())
    if total_hits == 0:
        raise ValueError(f"Lane {lane_id} has no key entries to analyze.")

    sorted_keys = sorted(key_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top_keys = sorted_keys[:top_k]
    primary_family: List[str] = [name for name, _ in top_keys]
    for name, _count in top_keys:
        if "_" not in name:
            continue
        root, mode = name.split("_", 1)
        pc = _normalize_pitch_class(root)
        norm_mode = _normalize_mode(mode)
        if pc is None or norm_mode is None:
            continue
        rel_pc, rel_mode = _relative_key(pc, norm_mode)
        rel_name = f"{PITCH_CLASS_NAMES[rel_pc]}_{rel_mode}"
        if rel_name in key_counts and rel_name not in primary_family:
            primary_family.append(rel_name)
        for delta in (-7, 7):
            nb_name = f"{PITCH_CLASS_NAMES[transpose_pc(pc, delta)]}_{norm_mode}"
            if nb_name in key_counts and nb_name not in primary_family:
                primary_family.append(nb_name)

    return KeyLaneStats(
        lane_id=lane_id,
        total_hits=total_hits,
        mode_counts=mode_counts,
        key_counts=key_counts,
        top_keys=top_keys,
        primary_family=primary_family,
    )


def compute_song_placement(lane_stats: KeyLaneStats, song_key: SongKey) -> KeySongPlacement:
    key_counts = lane_stats.key_counts
    total = lane_stats.total_hits or 1
    same_key_count = key_counts.get(song_key.key_name, 0)
    same_key_percent = same_key_count / total
    same_mode_count = sum(ct for name, ct in key_counts.items() if name.endswith(f"_{song_key.mode}"))
    same_mode_percent = same_mode_count / total if total else 0.0

    neighbor_keys: List[Dict[str, Any]] = []
    for key_name, count in key_counts.items():
        if key_name == song_key.key_name:
            continue
        if "_" not in key_name:
            continue
        root, _mode = key_name.split("_", 1)
        pc_other = _normalize_pitch_class(root)
        if pc_other is None:
            continue
        dist = _circle_distance(song_key.pitch_class, pc_other)
        if dist in (1, 2):
            neighbor_keys.append(
                {
                    "key_name": key_name,
                    "distance": dist,
                    "count": count,
                    "percent": count / total,
                }
            )
    neighbor_keys.sort(key=lambda x: (x["distance"], -x["count"], x["key_name"]))
    return KeySongPlacement(
        song_key_name=song_key.key_name,
        song_mode=song_key.mode,
        same_key_count=same_key_count,
        same_key_percent=same_key_percent,
        same_mode_percent=same_mode_percent,
        neighbor_keys=neighbor_keys,
    )


def build_key_advisory(stats: KeyLaneStats, placement: KeySongPlacement, song_key: SongKey) -> KeyAdvisory:
    primary_family = stats.primary_family
    label = "low_density_key"
    min_primary_dist = None
    for fam_name in primary_family:
        if "_" not in fam_name:
            continue
        root, _mode = fam_name.split("_", 1)
        pc = _normalize_pitch_class(root)
        if pc is None:
            continue
        dist = _circle_distance(song_key.pitch_class, pc)
        min_primary_dist = dist if min_primary_dist is None else min(min_primary_dist, dist)
    if song_key.key_name in primary_family:
        label = "primary_family"
    elif min_primary_dist is not None and min_primary_dist <= 1:
        label = "adjacent_family"

    suggested_transpositions: List[int] = []
    if label != "primary_family":
        deltas: List[int] = []
        for fam_name in primary_family:
            if "_" not in fam_name:
                continue
            root, fam_mode = fam_name.split("_", 1)
            fam_pc = _normalize_pitch_class(root)
            if fam_pc is None:
                continue
            delta = fam_pc - song_key.pitch_class
            # Normalize to a small +/- range
            if delta > 6:
                delta -= 12
            if delta < -6:
                delta += 12
            if abs(delta) <= 3 and (delta != 0 or fam_mode != song_key.mode):
                deltas.append(delta)
        deltas_sorted = sorted(set(deltas), key=lambda d: (abs(d), d))
        suggested_transpositions = deltas_sorted

    fam_disp = ", ".join(format_key_name(n) for n in primary_family) if primary_family else "the lane core"
    song_disp = song_key.full_name
    same_pct = placement.same_key_percent * 100.0
    mode_pct = placement.same_mode_percent * 100.0
    top_neighbors = placement.neighbor_keys[:2]
    nb_disp = ", ".join(f"{format_key_name(nb['key_name'])} ({nb['percent']*100:.1f}%)" for nb in top_neighbors) if top_neighbors else "none"
    trans_disp = ", ".join(f"{'+' if d>0 else ''}{d}" for d in suggested_transpositions) if suggested_transpositions else "none"
    if label == "primary_family":
        advisory_text = (
            f"Your key ({song_disp}) sits in the main key family for this lane ({fam_disp}); "
            f"~{same_pct:.1f}% of historical hits in this lane share this exact key and ~{mode_pct:.1f}% share your mode. "
            "This is a proven, lane-typical pocket for past hits."
        )
    elif label == "adjacent_family":
        advisory_text = (
            f"Your key ({song_disp}) is a close neighbor to the lane’s main key family ({fam_disp}); "
            f"~{same_pct:.1f}% of hits share this key and ~{mode_pct:.1f}% share your mode. "
            f"Neighboring lane pockets: {nb_disp}. "
            "It’s musically natural; if you want the most historically proven pocket, a small transpose toward the family works."
        )
    else:
        advisory_text = (
            f"Your key ({song_disp}) is uncommon for this lane (~{same_pct:.1f}% share this exact key; ~{mode_pct:.1f}% share your mode). "
            f"The main historical pocket clusters around {fam_disp}; nearby pockets: {nb_disp}. "
            f"If you want a lane-typical feel, consider small transpositions ({trans_disp}) toward that family."
        )

    return KeyAdvisory(
        advisory_label=label,
        advisory_text=advisory_text,
        suggested_key_family=primary_family,
        suggested_transpositions=suggested_transpositions,
    )


def build_sidecar_payload(lane_id: str, song_key: SongKey, lane_keys: List[SongKey], prefer_flat: bool = False) -> Dict[str, Any]:
    stats = compute_lane_stats(lane_id, lane_keys)
    placement = compute_song_placement(stats, song_key)
    advisory = build_key_advisory(stats, placement, song_key)
    neighbor_cache = precompute_neighbors(prefer_flat=prefer_flat)

    def _round(val: Optional[float], digits: int = 4) -> Optional[float]:
        if val is None:
            return None
        return round(float(val), digits)

    total_hits = max(1, stats.total_hits)
    historical_hit_medium = [
        {"key_name": format_key_name(name, prefer_flat=prefer_flat), "count": count, "percent": _round(count / total_hits)}
        for name, count in stats.top_keys
    ]

    # Rank target moves using musical relationships first, then lane density.
    key_density = stats.key_counts

    def _delta_to(target_pc: int) -> int:
        delta_val = target_pc - song_key.pitch_class
        if delta_val > 6:
            delta_val -= 12
        if delta_val < -6:
            delta_val += 12
        return delta_val

    candidate_moves: Dict[str, Dict[str, Any]] = {}

    # Relative major/minor (most natural)
    rel_pc, rel_mode = _relative_key(song_key.pitch_class, song_key.mode)
    rel_pct = key_density.get(f"{PITCH_CLASS_NAMES[rel_pc]}_{rel_mode}", 0) / total_hits
    rel_name = f"{PITCH_CLASS_NAMES[rel_pc]}_{rel_mode}"
    rel_entry = neighbor_cache.get((song_key.pitch_class, song_key.mode), {}).get("relative") or {}
    candidate_moves[rel_name] = {
        "target_key": format_key_name(rel_name, prefer_flat=prefer_flat),
        "mode": rel_mode,
        "semitone_delta": _delta_to(rel_pc),
        "reason": "relative",
        "score": 3.0 + (rel_pct or 0),
        "lane_percent": _round(rel_pct),
        "circle_distance": rel_entry.get("circle_distance"),
        "weight": RELATIONSHIP_WEIGHTS.get("relative", 1.0),
    }

    # Parallel mode
    par_pc, par_mode = _parallel_key(song_key.pitch_class, song_key.mode)
    par_pct = key_density.get(f"{PITCH_CLASS_NAMES[par_pc]}_{par_mode}", 0) / total_hits
    par_name = f"{PITCH_CLASS_NAMES[par_pc]}_{par_mode}"
    par_entry = neighbor_cache.get((song_key.pitch_class, song_key.mode), {}).get("parallel") or {}
    candidate_moves.setdefault(
        par_name,
        {
            "target_key": format_key_name(par_name, prefer_flat=prefer_flat),
            "mode": par_mode,
            "semitone_delta": _delta_to(par_pc),
            "reason": "parallel",
            "score": 2.5 + (par_pct or 0),
            "lane_percent": _round(par_pct),
            "circle_distance": par_entry.get("circle_distance"),
            "weight": RELATIONSHIP_WEIGHTS.get("parallel", 0.8),
        },
    )

    # Fifth neighbors (dominant/subdominant in same mode)
    for pc_nb, mode_nb in _fifth_neighbors(song_key.pitch_class, song_key.mode):
        nb_name = f"{PITCH_CLASS_NAMES[pc_nb]}_{mode_nb}"
        nb_pct = key_density.get(nb_name, 0) / total_hits
        fif_entries = neighbor_cache.get((song_key.pitch_class, song_key.mode), {}).get("fifths") or []
        matching_fif = next((f for f in fif_entries if f.get("pitch_class") == pc_nb and f.get("mode") == mode_nb), {})
        candidate_moves.setdefault(
            nb_name,
            {
                "target_key": format_key_name(nb_name, prefer_flat=prefer_flat),
                "mode": mode_nb,
                "semitone_delta": _delta_to(pc_nb),
                "reason": "fifth_neighbor",
                "score": 2.0 + (nb_pct or 0),
                "lane_percent": _round(nb_pct),
                "circle_distance": matching_fif.get("circle_distance"),
                "weight": RELATIONSHIP_WEIGHTS.get("fifth", 0.6),
            },
        )

    # Top historical hits (ensure coverage of lane medium)
    for name, count in stats.top_keys[:3]:
        if "_" not in name:
            continue
        root, mode = name.split("_", 1)
        target_pc = _normalize_pitch_class(root)
        if target_pc is None:
            continue
        pct = _round(count / total_hits)
        cand = candidate_moves.get(name)
        score = 1.0 + (pct or 0)
        entry = {
            "target_key": format_key_name(name, prefer_flat=prefer_flat),
            "mode": mode,
            "semitone_delta": _delta_to(target_pc),
            "reason": "historical_hit_medium",
            "score": score,
            "lane_percent": pct,
            "weight": RELATIONSHIP_WEIGHTS.get("historical_hit_medium", 0.0),
        }
        if cand:
            # Preserve higher-score relationship but keep lane percent
            cand.setdefault("lane_percent", pct)
        else:
            candidate_moves[name] = entry

    # Add rationale tags and chord-fit hints
    def _rationale_tags(reason: str) -> List[str]:
        return {
            "relative": ["relative_major_minor", "shared_scale_notes", "easy_vocal_move"],
            "parallel": ["parallel_mode", "same_tonic", "color_shift"],
            "fifth_neighbor": ["circle_of_fifths", "adjacent_key", "common_progressions"],
            "historical_hit_medium": ["lane_top_keys", "proven_lane_choice"],
        }.get(reason, [reason or "lane_top"])

    def _chord_fit_hint(reason: str) -> str:
        if reason == "relative":
            return "Relative move; most diatonic chords overlap (e.g., vi in major to I in relative minor)."
        if reason == "parallel":
            return "Parallel mode; tonic stays the same, color shifts between major/minor."
        if reason == "fifth_neighbor":
            return "Adjacent on circle of fifths; shares dominant/subdominant gravity."
        return "Lane-top key; aligns with historical medium for this lane."

    for m in candidate_moves.values():
        reason = m.get("reason", "")
        m["rationale_tags"] = _rationale_tags(reason)
        m["chord_fit_hint"] = _chord_fit_hint(reason)

    target_key_moves = sorted(
        candidate_moves.values(),
        key=lambda m: (-m.get("score", 0), -float(m.get("lane_percent") or 0), abs(m.get("semitone_delta", 0))),
    )

    # Lane shape/entropy diagnostics + mode split + fifths chain
    import math
    key_total = max(1, stats.total_hits)
    probs = [cnt / key_total for cnt in stats.key_counts.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    max_entropy = math.log2(len(probs)) if probs else 1.0
    flatness = entropy / max_entropy if max_entropy > 0 else 0.0
    mode_split = {
        "major_share": stats.mode_counts.get("major", 0) / key_total,
        "minor_share": stats.mode_counts.get("minor", 0) / key_total,
    }
    def _top_by_mode(mode_filter: str, top_n: int = 3) -> List[str]:
        filtered = [(k, c) for k, c in stats.key_counts.items() if k.endswith(f"_{mode_filter}")]
        filtered.sort(key=lambda kv: (-kv[1], kv[0]))
        return [format_key_name(k, prefer_flat=prefer_flat) for k, _ in filtered[:top_n]]

    mode_top_keys = {
        "major": _top_by_mode("major"),
        "minor": _top_by_mode("minor"),
    }

    def _circle_pos(pc: int) -> int:
        return circle_distance(pc, 0)
    fifths_chain = [
        format_key_name(name, prefer_flat=prefer_flat)
        for name, _ in sorted(stats.key_counts.items(), key=lambda kv: (_circle_pos(_normalize_pitch_class(kv[0].split("_", 1)[0]) or 0), -kv[1]))
    ][:6]

    payload = {
        "key_analysis_version": KEY_ANALYSIS_VERSION,
        "lane_id": lane_id,
        "song_key": {
            "root_name": format_key_name(song_key.root_name, prefer_flat=prefer_flat).split()[0],
            "mode": song_key.mode,
            "full_name": format_key_name(song_key.key_name, prefer_flat=prefer_flat),
            "pitch_class": song_key.pitch_class,
        },
        "lane_stats": {
            "total_hits": stats.total_hits,
            "mode_counts": stats.mode_counts,
            "top_keys": stats.top_keys,
            "historical_hit_medium": historical_hit_medium,
            "primary_family": stats.primary_family,
            "key_counts": stats.key_counts,
            "lane_shape": {
                "entropy": _round(entropy),
                "flatness": _round(flatness),
                "mode_split": mode_split,
            },
            "mode_top_keys": mode_top_keys,
            "fifths_chain": fifths_chain,
        },
        "song_placement": {
            "key_name": placement.song_key_name,
            "same_key_count": placement.same_key_count,
            "same_key_percent": _round(placement.same_key_percent),
            "same_mode_percent": _round(placement.same_mode_percent),
            "neighbor_keys": [
                {
                    "key_name": nb["key_name"],
                    "distance": nb["distance"],
                    "count": nb["count"],
                    "percent": _round(nb["percent"]),
                }
                for nb in placement.neighbor_keys
            ],
        },
        "advisory": {
            "advisory_label": advisory.advisory_label,
            "advisory_text": advisory.advisory_text,
            "suggested_key_family": advisory.suggested_key_family,
            "suggested_transpositions": advisory.suggested_transpositions,
            "target_key_moves": target_key_moves,
        },
    }
    return payload


def derive_out_path(song_id: str, out: Optional[str], out_dir: Optional[str]) -> Path:
    if out:
        return Path(out).expanduser().resolve()
    suffix = names.key_norms_sidecar_suffix()
    base = Path(out_dir).expanduser().resolve() if out_dir else Path.cwd()
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{song_id}{suffix}"


def _validate_payload(payload: dict) -> list[str]:
    """Best-effort schema validation if jsonschema is available."""
    warnings: list[str] = []
    if jsonschema is None:
        return warnings
    schema_path = Path(__file__).resolve().parent / "key_norms_schema.json"
    try:
        schema = json.loads(schema_path.read_text())
        jsonschema.validate(payload, schema)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"schema_validation_error:{exc}")
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute key lane norms + advisory sidecar.")
    ap.add_argument("--song-id", required=True, help="Song identifier (used for filenames/default lookup).")
    ap.add_argument("--lane-id", required=True, help="Lane identifier (e.g., tier1_modern or EchoTier_1_YearEnd_Top40).")
    ap.add_argument("--song-key", default=None, help="Optional song key override (e.g., 'C# major'); defaults to key/mode in features JSON.")
    ap.add_argument("--features-json", default=None, help="Optional features/client JSON path containing key/mode.")
    ap.add_argument("--db", default=str(get_historical_echo_db_path()), help="Path to historical_echo.db with lane key data.")
    ap.add_argument("--out", help="Exact output path for key norms sidecar JSON.")
    ap.add_argument("--out-dir", help="Output directory (defaults to current working directory).")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing sidecar if present.")
    ap.add_argument("--prefer-flat", action="store_true", help="Prefer flat key spelling in outputs (if applicable).")
    ap.add_argument("--timeout-seconds", type=float, default=None, help="Optional timeout for DB/processing (env KEY_NORMS_TIMEOUT).")
    add_log_sandbox_arg(ap)
    defaults = {action.dest: action.default for action in ap._actions if action.dest != "help"}
    args = ap.parse_args()
    args = _apply_env_overrides(args, defaults)

    apply_log_sandbox_env(args)
    log = make_logger("key_norms_sidecar")
    if args.timeout_seconds is None:
        env_timeout = os.getenv("KEY_NORMS_TIMEOUT")
        if env_timeout:
            try:
                args.timeout_seconds = float(env_timeout)
            except Exception:
                args.timeout_seconds = None

    out_path = derive_out_path(args.song_id, args.out, args.out_dir)
    if out_path.exists() and not args.overwrite:
        log(f"[SKIP] key norms sidecar already exists: {out_path}")
        return 0

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    features_path = Path(args.features_json).expanduser().resolve() if args.features_json else None
    search_dir = out_path.parent

    log_stage_start(log, "key_norms_sidecar", song_id=args.song_id, lane_id=args.lane_id, db=str(db_path), out=str(out_path))
    conn = sqlite3.connect(str(db_path))
    song_key = resolve_song_key(args.song_key, features_path, args.song_id, search_dir)
    lane_keys = load_lane_keys(conn, args.lane_id)
    if not lane_keys:
        raise SystemExit(f"No lane key data found for lane_id={args.lane_id}")

    payload = build_sidecar_payload(args.lane_id, song_key, lane_keys, prefer_flat=args.prefer_flat)
    validation_warnings = _validate_payload(payload)
    if validation_warnings:
        log(f"[WARN] key norms schema warnings: {validation_warnings}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log(f"[OK] Wrote key norms sidecar: {out_path}")

    log_stage_end(log, "key_norms_sidecar", status="ok", out=str(out_path))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
