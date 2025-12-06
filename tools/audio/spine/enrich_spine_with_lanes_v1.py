#!/usr/bin/env python3
"""
enrich_spine_with_lanes_v1.py

Add lane columns to the Historical Echo Core Spine v1 master CSV.

Inputs:
- data/spine/spine_master_v1.csv  (Core 1600 with audio features)

Required columns:
- tempo        (float BPM)
- valence      (0–1)
- energy       (0–1)
- danceability (0–1)
- loudness     (dB, negative)
- year         (int)

Optional columns (lanes fall back to 'unknown' if missing):
- acousticness
- instrumentalness
- speechiness
- duration_ms
- key
- mode

Outputs:
- data/spine/spine_master_v1_lanes.csv

Added columns:
- tempo_core_bpm
- tempo_multiplier
- tempo_band
- valence_band
- energy_band
- danceability_band
- loudness_band
- era_bucket
- duration_sec
- duration_band
- acousticness_band
- instrumental_flag
- speechiness_band
- mode_simple
- key_mode_label
- has_audio_features
- lane_ready
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from shared.config.paths import get_spine_root

KEY_NAMES = {
    0: "C",
    1: "C#",
    2: "D",
    3: "Eb",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "Ab",
    9: "A",
    10: "Bb",
    11: "B",
}


def parse_float(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    v = val.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_int(val: Optional[str]) -> Optional[int]:
    if val is None:
        return None
    v = val.strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def normalize_tempo(tempo_raw: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    """
    Normalize raw tempo into a comfortable pop feel range (80–170 BPM)
    via half/double-time. Returns (tempo_core_bpm, tempo_multiplier).

    Examples:
    - 68  -> 136 (core), multiplier ~ 0.5
    - 90  -> 90  (core), multiplier ~ 1.0
    - 178 -> 89  (core), multiplier ~ 2.0
    """
    if tempo_raw is None or tempo_raw <= 0:
        return None, None

    core = tempo_raw
    multiplier = 1.0

    # Bring up very slow tempi by doubling
    while core < 80.0:
        core *= 2.0
        multiplier *= 2.0
        if core > 400.0:
            break

    # Bring down very fast tempi by halving
    while core > 170.0:
        core /= 2.0
        multiplier /= 2.0
        if core < 20.0:
            break

    # Snap multiplier to simple values for interpretability
    if multiplier < 0.75:
        approx = 0.5
    elif multiplier > 1.5:
        approx = 2.0
    else:
        approx = 1.0

    return core, approx


def tempo_to_band(tempo_core: Optional[float]) -> str:
    if tempo_core is None:
        return "unknown"
    if tempo_core < 90.0:
        return "slow"
    if tempo_core < 120.0:
        return "mid"
    if tempo_core < 140.0:
        return "fast"
    return "very_fast"


def valence_to_band(val: Optional[float]) -> str:
    if val is None:
        return "unknown"
    if val < 0.33:
        return "low"
    if val <= 0.66:
        return "mid"
    return "high"


def energy_to_band(val: Optional[float]) -> str:
    if val is None:
        return "unknown"
    if val < 0.33:
        return "low"
    if val <= 0.66:
        return "mid"
    return "high"


def danceability_to_band(val: Optional[float]) -> str:
    if val is None:
        return "unknown"
    if val < 0.4:
        return "low"
    if val <= 0.7:
        return "mid"
    return "high"


def loudness_to_band(loud: Optional[float]) -> str:
    if loud is None:
        return "unknown"
    if loud < -11.0:
        return "dynamic"
    if loud <= -7.0:
        return "modern_loud"
    return "crushed"


def year_to_era_bucket(year: Optional[int]) -> str:
    if year is None:
        return "unknown"
    if 1985 <= year <= 1989:
        return "late_80s"
    if 1990 <= year <= 1999:
        return "90s"
    if 2000 <= year <= 2009:
        return "00s"
    if 2010 <= year <= 2019:
        return "10s"
    if 2020 <= year <= 2029:
        return "20s"
    return "unknown"


def duration_to_band(sec: Optional[float]) -> str:
    if sec is None:
        return "unknown"
    if sec < 150.0:
        return "short"
    if sec < 240.0:
        return "mid"
    if sec < 300.0:
        return "long"
    return "epic"


def acoustic_to_band(val: Optional[float]) -> str:
    if val is None:
        return "unknown"
    if val < 0.3:
        return "low"
    if val <= 0.7:
        return "mid"
    return "high"


def instrumental_to_flag(val: Optional[float]) -> str:
    if val is None:
        return "unknown"
    return "True" if val > 0.5 else "False"


def speechiness_to_band(val: Optional[float]) -> str:
    if val is None:
        return "unknown"
    if val < 0.33:
        return "low"
    if val <= 0.66:
        return "mid"
    return "high"


def mode_to_simple(mode_val: Optional[int]) -> str:
    if mode_val is None:
        return "unknown"
    if mode_val == 1:
        return "major"
    if mode_val == 0:
        return "minor"
    return "ambiguous"


def key_mode_to_label(key_val: Optional[int], mode_val: Optional[int]) -> str:
    if key_val is None or mode_val is None:
        return "unknown"
    name = KEY_NAMES.get(key_val)
    if name is None:
        return "unknown"
    if mode_val == 1:
        qual = "major"
    elif mode_val == 0:
        qual = "minor"
    else:
        return "unknown"
    return f"{name}_{qual}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add tempo/valence/energy/danceability/loudness/era + extra lanes to spine_master_v1 CSV."
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(get_spine_root() / "spine_master_v1.csv"),
        help=f"Input master spine CSV (default: {get_spine_root() / 'spine_master_v1.csv'})",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default=str(get_spine_root() / "spine_master_v1_lanes.csv"),
        help=f"Output CSV with lane columns (default: {get_spine_root() / 'spine_master_v1_lanes.csv'})",
    )

    args = parser.parse_args()
    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    print(f"[INFO] Loading master spine from {in_path} ...")
    with in_path.open("r", encoding="utf-8", newline="") as f_in:
        reader = csv.DictReader(f_in)
        rows: List[Dict[str, Any]] = list(reader)
        fieldnames = reader.fieldnames or []

    required = {"tempo", "valence", "energy", "danceability", "loudness", "year"}
    missing = required - set(fieldnames)
    if missing:
        raise SystemExit(
            f"[ERROR] Input CSV missing required columns: {sorted(missing)}. "
            "Make sure spine_master_v1.csv includes Spotify-style features."
        )

    added_cols = [
        "tempo_core_bpm",
        "tempo_multiplier",
        "tempo_band",
        "valence_band",
        "energy_band",
        "danceability_band",
        "loudness_band",
        "era_bucket",
        "duration_sec",
        "duration_band",
        "acousticness_band",
        "instrumental_flag",
        "speechiness_band",
        "mode_simple",
        "key_mode_label",
        "has_audio_features",
        "lane_ready",
    ]
    out_fieldnames = fieldnames + added_cols

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Writing enriched master spine with lanes to {out_path} ...")

    n_rows = 0
    n_with_any_audio = 0

    with out_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)
        writer.writeheader()

        for row in rows:
            # Core numeric parses
            tempo_raw = parse_float(row.get("tempo"))
            val = parse_float(row.get("valence"))
            energy = parse_float(row.get("energy"))
            dance = parse_float(row.get("danceability"))
            loud = parse_float(row.get("loudness"))
            year = parse_int(row.get("year"))

            # Optional numeric parses
            acoustic = parse_float(row.get("acousticness"))
            instr = parse_float(row.get("instrumentalness"))
            speech = parse_float(row.get("speechiness"))
            dur_ms = parse_float(row.get("duration_ms"))
            key_val = parse_int(row.get("key"))
            mode_val = parse_int(row.get("mode"))

            # Audio presence
            if any(
                x is not None
                for x in (tempo_raw, val, energy, dance, loud, acoustic, instr, speech, dur_ms)
            ):
                n_with_any_audio += 1
                has_audio_features = "True"
            else:
                has_audio_features = "False"

            # Tempo / feel
            tempo_core, tempo_mult = normalize_tempo(tempo_raw)
            row["tempo_core_bpm"] = f"{tempo_core:.3f}" if tempo_core is not None else ""
            row["tempo_multiplier"] = f"{tempo_mult:.1f}" if tempo_mult is not None else ""

            row["tempo_band"] = tempo_to_band(tempo_core)
            row["valence_band"] = valence_to_band(val)
            row["energy_band"] = energy_to_band(energy)
            row["danceability_band"] = danceability_to_band(dance)
            row["loudness_band"] = loudness_to_band(loud)
            row["era_bucket"] = year_to_era_bucket(year)

            # Duration
            if dur_ms is not None:
                sec = round(dur_ms / 1000.0)
                row["duration_sec"] = str(int(sec))
                row["duration_band"] = duration_to_band(sec)
            else:
                row["duration_sec"] = ""
                row["duration_band"] = "unknown"

            # Acoustic / instrumental / speechiness
            row["acousticness_band"] = acoustic_to_band(acoustic)
            row["instrumental_flag"] = instrumental_to_flag(instr)
            row["speechiness_band"] = speechiness_to_band(speech)

            # Key / mode
            row["mode_simple"] = mode_to_simple(mode_val)
            row["key_mode_label"] = key_mode_to_label(key_val, mode_val)

            # Lane readiness: enough info for core comparisons
            lane_ready = (
                tempo_core is not None
                and val is not None
                and energy is not None
                and dance is not None
            )
            row["has_audio_features"] = has_audio_features
            row["lane_ready"] = "True" if lane_ready else "False"

            writer.writerow(row)
            n_rows += 1

    print("[INFO] Lane enrichment summary:")
    print(f"  Rows processed         : {n_rows}")
    print(f"  Rows with any audio    : {n_with_any_audio}")
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
