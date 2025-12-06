#!/usr/bin/env python3
"""
Build Tier 1 audio backfill from Patrick Year-End Spotify features.

Inputs:
    - Core Tier 1 spine metadata (canonical):
        data/public/spine/spine_core_tracks_v1.csv
    - Patrick Year-End Hot 100 features:
        data/private/local_assets/external/year_end/year_end_hot_100_spotify_features_patrick_1960_2020.csv

Matching key:
    (year, normalized artist, normalized title)

Output:
    data/public/spine/backfill/spine_audio_from_patrick_v1.csv

Columns:
    spine_track_id,
    tempo, loudness, danceability, energy, valence,
    acousticness, instrumentalness, liveness, speechiness,
    duration_ms, key, mode, time_signature
(only those present in the Patrick CSV will be written)
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from shared.config.paths import get_external_data_root, get_spine_root


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    if not s:
        return ""
    # Strip accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Replace ampersand patterns
    s = s.replace("&", " and ")
    # Remove punctuation-like characters
    cleaned_chars = []
    for ch in s:
        if ch.isalnum() or ch.isspace():
            cleaned_chars.append(ch)
        # else drop punctuation
    s = "".join(cleaned_chars)
    # Collapse whitespace
    s = " ".join(s.split())
    return s


def pick_column(candidates: List[str], fieldnames: List[str], required: bool = False) -> Optional[str]:
    lower_map = {f.lower(): f for f in fieldnames}
    for cand in candidates:
        c_lower = cand.lower()
        if c_lower in lower_map:
            return lower_map[c_lower]
    if required:
        raise SystemExit(
            f"[build_spine_audio_from_patrick_v1] Required column not found. "
            f"Tried: {candidates} in {fieldnames}"
        )
    return None


def build_core_index(core_path: Path) -> Dict[Tuple[int, str, str], str]:
    """
    Build mapping:
        (year, norm_artist, norm_title) -> spine_track_id
    from spine_core_tracks_v1.csv
    """
    if not core_path.exists():
        raise SystemExit(f"[build_spine_audio_from_patrick_v1] Missing core CSV: {core_path}")

    with core_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(
                f"[build_spine_audio_from_patrick_v1] Empty or headerless CSV: {core_path}"
            )

        required_fields = ["spine_track_id", "year", "artist", "title"]
        for rf in required_fields:
            if rf not in reader.fieldnames:
                raise SystemExit(
                    f"[build_spine_audio_from_patrick_v1] Core CSV missing required field '{rf}' "
                    f"in {core_path}"
                )

        index: Dict[Tuple[int, str, str], str] = {}

        for row in reader:
            spine_id = (row.get("spine_track_id") or "").strip()
            if not spine_id:
                continue

            year_str = (row.get("year") or "").strip()
            if not year_str:
                continue
            try:
                year = int(year_str)
            except ValueError:
                continue

            artist_norm = normalize_text(row.get("artist", ""))
            title_norm = normalize_text(row.get("title", ""))
            if not artist_norm or not title_norm:
                continue

            key = (year, artist_norm, title_norm)
            index[key] = spine_id

        print(
            f"[build_spine_audio_from_patrick_v1] Core index built: "
            f"{len(index)} key entries."
        )
        return index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build spine_audio_from_patrick_v1.csv from Patrick Year-End Spotify features."
    )
    parser.add_argument(
        "--core",
        default=str(get_spine_root() / "spine_core_tracks_v1.csv"),
        help="Core Tier 1 spine CSV (canonical metadata).",
    )
    parser.add_argument(
        "--patrick",
        default=str(get_external_data_root() / "year_end/year_end_hot_100_spotify_features_patrick_1960_2020.csv"),
        help="Patrick Year-End Hot 100 Spotify features CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(get_spine_root() / "backfill" / "spine_audio_from_patrick_v1.csv"),
        help="Output CSV for Patrick audio backfill.",
    )

    args = parser.parse_args()

    core_path = Path(args.core)
    patrick_path = Path(args.patrick)
    out_path = Path(args.out)

    core_index = build_core_index(core_path)

    if not patrick_path.exists():
        raise SystemExit(f"[build_spine_audio_from_patrick_v1] Missing Patrick CSV: {patrick_path}")

    print(f"[build_spine_audio_from_patrick_v1] Loading Patrick dataset from: {patrick_path}")
    print("[build_spine_audio_from_patrick_v1] NOTE: Using latin-1 encoding for this CSV.")

    # KEY CHANGE: use latin-1 to avoid UnicodeDecodeError on characters like é
    with patrick_path.open("r", newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(
                f"[build_spine_audio_from_patrick_v1] Empty or headerless CSV: {patrick_path}"
            )

        fieldnames_patrick = list(reader.fieldnames)

        # Detect columns
        year_col = pick_column(
            ["year", "Year", "year_end", "year_end_year"],
            fieldnames_patrick,
            required=True,
        )
        artist_col = pick_column(
            ["artist", "Artist", "performer", "Performer", "primary_artist"],
            fieldnames_patrick,
            required=True,
        )
        title_col = pick_column(
            ["title", "Title", "song", "Song", "track_name"],
            fieldnames_patrick,
            required=True,
        )

        # Audio feature columns we care about (only keep those that exist)
        AUDIO_FEATURE_CANDIDATES = [
            "tempo",
            "loudness",
            "danceability",
            "energy",
            "valence",
            "acousticness",
            "instrumentalness",
            "liveness",
            "speechiness",
            "duration_ms",
            "key",
            "mode",
            "time_signature",
        ]

        audio_feature_cols: List[str] = [
            c for c in AUDIO_FEATURE_CANDIDATES if c in fieldnames_patrick
        ]

        # Also pass through Spotify ID if present (optional)
        spotify_id_col = pick_column(
            ["spotify_id", "Spotify_ID", "spotify_track_id", "track_id"],
            fieldnames_patrick,
            required=False,
        )
        id_cols: List[str] = []
        if spotify_id_col:
            id_cols.append(spotify_id_col)

        print(
            f"[build_spine_audio_from_patrick_v1] Using columns: "
            f"year={year_col}, artist={artist_col}, title={title_col}"
        )
        print(
            f"[build_spine_audio_from_patrick_v1] Audio features found: {audio_feature_cols}"
        )
        if id_cols:
            print(
                f"[build_spine_audio_from_patrick_v1] ID columns included: {id_cols}"
            )

        # Build mapping from spine_track_id -> audio feature dict
        backfill_by_spine_id: Dict[str, Dict[str, str]] = {}
        total_rows = 0
        matched_rows = 0

        for row in reader:
            total_rows += 1

            year_str = (row.get(year_col) or "").strip()
            try:
                year = int(year_str)
            except ValueError:
                continue

            artist_norm = normalize_text(row.get(artist_col, ""))
            title_norm = normalize_text(row.get(title_col, ""))
            if not artist_norm or not title_norm:
                continue

            key = (year, artist_norm, title_norm)
            spine_id = core_index.get(key)
            if not spine_id:
                continue

            # Collect feature values
            feat: Dict[str, str] = {}
            for col in audio_feature_cols:
                val = row.get(col, "")
                if val not in ("", None):
                    feat[col] = val

            for col in id_cols:
                val = row.get(col, "")
                if val not in ("", None):
                    feat[col] = val

            if not feat:
                # Nothing useful to store
                continue

            # If duplicates, last one wins; this is fine for now.
            backfill_by_spine_id[spine_id] = feat
            matched_rows += 1

        print(
            f"[build_spine_audio_from_patrick_v1] Patrick rows scanned: {total_rows}, "
            f"matched to core spine: {matched_rows}, "
            f"unique spine_track_ids with backfill: {len(backfill_by_spine_id)}"
        )

    # Write backfill CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames_out: List[str] = ["spine_track_id"]
    # Preserve column ordering: features first, then IDs
    for col in audio_feature_cols + id_cols:
        if col not in fieldnames_out:
            fieldnames_out.append(col)

    print(f"[build_spine_audio_from_patrick_v1] Writing backfill to: {out_path}")

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames_out)
        writer.writeheader()

        for spine_id, feat in backfill_by_spine_id.items():
            row_out = {fn: "" for fn in fieldnames_out}
            row_out["spine_track_id"] = spine_id
            for col, val in feat.items():
                if col in fieldnames_out:
                    row_out[col] = val
            writer.writerow(row_out)

    print(
        f"[build_spine_audio_from_patrick_v1] Done. "
        f"Wrote {len(backfill_by_spine_id)} rows to {out_path}"
    )


if __name__ == "__main__":
    main()
