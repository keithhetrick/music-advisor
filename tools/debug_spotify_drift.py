#!/usr/bin/env python3
"""
tools/debug_spotify_drift.py

Debug drift between local .features.json and offline Spotify/Kaggle
audio features for arbitrary year slices.

This is the generalized version of debug_spotify_drift_1985_1986.py.

Usage example:

  python tools/debug_spotify_drift.py \
    --features-root features_output/2025/11/22 \
    --spotify-dir calibration/spotify_offline/1985_1986 \
    --years 1985 1986

You can point --spotify-dir at any folder produced by your
build_offline_spotify_features.py script; this script will pick
the latest *.csv in that directory.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Dict, Any, List, Optional, Sequence


# ------------------------- helpers ------------------------- #

def normalize_name(s: str) -> str:
    """
    Same normalizer concept as hci_compare_targets.py:
    - lowercase
    - '&' -> 'and'
    - strip quotes / apostrophes / backticks
    - remove parentheses
    - non-alphanumeric -> space
    - collapse whitespace
    - fix split contractions like 'don t' -> 'dont'
    """
    import re

    s = (s or "").lower()
    s = s.replace("&", "and")
    s = re.sub(r"[’'\"`]", "", s)
    s = re.sub(r"[()]", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _fix_contractions(s)
    return s


def _fix_contractions(norm: str) -> str:
    tokens = norm.split()
    out = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            pair = (tokens[i], tokens[i + 1])

            if pair[0] in {
                "don", "can", "didn", "doesn",
                "isn", "wasn", "shouldn", "couldn",
                "wouldn", "ain"
            } and pair[1] == "t":
                out.append(pair[0] + "t")
                i += 2
                continue

            if pair == ("let", "s"):
                out.append("lets")
                i += 2
                continue

        out.append(tokens[i])
        i += 1

    return " ".join(out)


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def summarize_metric(name, values, is_pct=False, tol=None):
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        print(f"{name}: no data\n")
        return
    unit = " %" if is_pct else ""
    print(f"{name}:")
    print(f"  count  : {len(vals)}")
    print(f"  mean   : {mean(vals):.3f}{unit}")
    print(f"  median : {median(vals):.3f}{unit}")
    print(f"  min    : {min(vals):.3f}{unit}")
    print(f"  max    : {max(vals):.3f}{unit}")
    if tol is not None:
        pass_count = sum(1 for v in vals if abs(v) <= tol)
        pct = 100 * pass_count / len(vals)
        tol_unit = "%" if is_pct else ""
        print(f"  PASS   : {pass_count} / {len(vals)} "
              f"({pct:.1f}%) within ±{tol}{tol_unit}")
    print("")


# ------------------------- main ------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Debug drift between local .features.json and offline "
            "Spotify/Kaggle audio features for arbitrary year slices."
        )
    )
    ap.add_argument(
        "--features-root",
        default="features_output/2025/11/22",
        help="Root directory of local .features.json files "
             "(default: features_output/2025/11/22)",
    )
    ap.add_argument(
        "--spotify-dir",
        default="calibration/spotify_offline/1985_1986",
        help="Directory containing offline Spotify features CSVs "
             "(default: calibration/spotify_offline/1985_1986). "
             "The latest *.csv in this directory will be used.",
    )
    ap.add_argument(
        "--years",
        nargs="+",
        type=int,
        required=True,
        help="Years to include (e.g. 1985 1986). Required.",
    )
    ap.add_argument(
        "--tempo-tol-pct",
        type=float,
        default=5.0,
        help="Tempo drift tolerance in percent (default: 5.0)",
    )
    ap.add_argument(
        "--loudness-tol-db",
        type=float,
        default=2.0,
        help="Loudness difference tolerance in dB (default: 2.0)",
    )
    ap.add_argument(
        "--metric-tol",
        type=float,
        default=0.10,
        help="Danceability/Energy/Valence absolute diff tolerance "
             "(default: 0.10)",
    )

    args = ap.parse_args()

    features_root = Path(args.features_root)
    spotify_dir = Path(args.spotify_dir)
    years = set(args.years)

    if not features_root.exists():
        raise SystemExit(f"[ERROR] features-root does not exist: {features_root}")
    if not spotify_dir.exists():
        raise SystemExit(f"[ERROR] spotify-dir does not exist: {spotify_dir}")

    print(f"[INFO] Years filter: {sorted(years)}\n")

    # ------------------------------------------------------------------
    # 1) Local features
    # ------------------------------------------------------------------
    local: Dict[str, Dict[str, Any]] = {}
    feat_files = sorted(features_root.rglob("*.features.json"))
    print(f"[INFO] Found {len(feat_files)} local .features.json files under {features_root}")

    for f in feat_files:
        try:
            blob = json.loads(f.read_text())
        except Exception:
            continue

        # Expect: features_root/<year>/<slug_dir>/file.features.json
        rel = f.relative_to(features_root)
        parts = rel.parts
        if not parts:
            continue

        try:
            year = int(parts[0])
        except Exception:
            continue
        if year not in years:
            continue

        slug_dir = f.parent.name
        slug_parts = slug_dir.split("__")
        if len(slug_parts) < 2:
            continue

        year_artist = slug_parts[0]  # e.g. "1985_a_ha"
        title_slug = slug_parts[1]   # e.g. "take_on_me"

        artist_bits = year_artist.split("_")[1:]  # drop year
        artist_slug = " ".join(artist_bits)
        title_name = title_slug.replace("_", " ")

        key = f"{year}|{normalize_name(artist_slug)}|{normalize_name(title_name)}"

        # Features may be flat or wrapped
        if isinstance(blob, dict) and "features_full" in blob:
            feats = blob.get("features_full") or {}
        else:
            feats = blob

        if not isinstance(feats, dict):
            continue

        local[key] = {
            "tempo_bpm":     safe_float(feats.get("tempo_bpm")),
            "duration_sec":  safe_float(feats.get("duration_sec")),
            "loudness_LUFS": safe_float(feats.get("loudness_LUFS")),
            "danceability":  safe_float(feats.get("danceability")),
            "energy":        safe_float(feats.get("energy")),
            "valence":       safe_float(feats.get("valence")),
            "path":          str(f),
        }

    print(f"[INFO] Local feature keys (after year filter): {len(local)}\n")

    # ------------------------------------------------------------------
    # 2) Offline Spotify features
    # ------------------------------------------------------------------
    offline_files = sorted(spotify_dir.glob("*.csv"))
    if not offline_files:
        raise SystemExit(f"[ERROR] No CSV files found under {spotify_dir}")

    spotify_csv = offline_files[-1]
    print(f"[INFO] Using offline Spotify features CSV: {spotify_csv}\n")

    spotify: Dict[str, Dict[str, Any]] = {}
    with spotify_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row.get("year", "") or 0)
            except Exception:
                continue
            if year not in years:
                continue

            artist = row.get("artist", "") or row.get("artists", "")
            title = row.get("title", "") or row.get("name", "")
            key = f"{year}|{normalize_name(artist)}|{normalize_name(title)}"

            spotify[key] = {
                "tempo":        safe_float(row.get("tempo")),
                "loudness":     safe_float(row.get("loudness")),
                "danceability": safe_float(row.get("danceability")),
                "energy":       safe_float(row.get("energy")),
                "valence":      safe_float(row.get("valence")),
            }

    print(f"[INFO] Offline Spotify keys (after year filter): {len(spotify)}\n")

    # ------------------------------------------------------------------
    # 3) Match & compute drift
    # ------------------------------------------------------------------
    matched_keys = sorted(set(local.keys()) & set(spotify.keys()))
    local_only   = sorted(set(local.keys()) - set(spotify.keys()))
    spotify_only = sorted(set(spotify.keys()) - set(local.keys()))

    print("=== MATCH SUMMARY (Local features vs Offline Spotify) ===")
    print(f"Matched songs      : {len(matched_keys)}")
    print(f"Local-only keys    : {len(local_only)}")
    print(f"Spotify-only keys  : {len(spotify_only)}")
    print("")

    tempo_drift_pct: List[float] = []
    loudness_diff_db: List[float] = []
    dance_diff: List[float] = []
    energy_diff: List[float] = []
    valence_diff: List[float] = []

    for key in matched_keys:
        lf = local[key]
        sf = spotify[key]

        # Tempo drift %
        if lf["tempo_bpm"] is not None and sf["tempo"] not in (None, 0.0):
            tempo_drift = (lf["tempo_bpm"] - sf["tempo"]) / sf["tempo"] * 100.0
            tempo_drift_pct.append(tempo_drift)

        # Loudness diff
        if lf["loudness_LUFS"] is not None and sf["loudness"] is not None:
            loudness_diff_db.append(lf["loudness_LUFS"] - sf["loudness"])

        # Danceability / Energy / Valence
        if lf["danceability"] is not None and sf["danceability"] is not None:
            dance_diff.append(lf["danceability"] - sf["danceability"])
        if lf["energy"] is not None and sf["energy"] is not None:
            energy_diff.append(lf["energy"] - sf["energy"])
        if lf["valence"] is not None and sf["valence"] is not None:
            valence_diff.append(lf["valence"] - sf["valence"])

    # ------------------------------------------------------------------
    # 4) Summaries
    # ------------------------------------------------------------------
    print("=== DRIFT SUMMARY (Local vs Spotify) ===\n")

    summarize_metric(
        "Tempo drift (local tempo_bpm vs Spotify tempo)",
        tempo_drift_pct,
        is_pct=True,
        tol=args.tempo_tol_pct,
    )

    summarize_metric(
        "Loudness difference (local LUFS - Spotify dB)",
        loudness_diff_db,
        is_pct=False,
        tol=args.loudness_tol_db,
    )

    summarize_metric(
        "Danceability difference (local - Spotify)",
        dance_diff,
        is_pct=False,
        tol=args.metric_tol,
    )

    summarize_metric(
        "Energy difference (local - Spotify)",
        energy_diff,
        is_pct=False,
        tol=args.metric_tol,
    )

    summarize_metric(
        "Valence difference (local - Spotify)",
        valence_diff,
        is_pct=False,
        tol=args.metric_tol,
    )


if __name__ == "__main__":
    main()
