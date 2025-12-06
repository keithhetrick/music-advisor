#!/usr/bin/env python3
"""
Build Tier 1 audio backfill from the 'hot_100_lyrics_audio_2000_2023.csv' dataset.

Inputs:
    - Core Tier 1 spine metadata (canonical):
        data/spine/spine_core_tracks_v1.csv
    - Hot 100 lyrics+audio dataset:
        data/external/lyrics/hot_100_lyrics_audio_2000_2023.csv

Assumptions (based on inventory):
    - Columns include something like:
        year, song, band_singer, titletext, lyrics, <audio feature columns...>
    - Coverage roughly 2000–2023.

Matching key:
    (year, normalized artist, normalized title)

Output:
    data/spine/backfill/spine_audio_from_hot100_lyrics_audio_v1.csv

Columns:
    spine_track_id,
    tempo, loudness, danceability, energy, valence,
    acousticness, instrumentalness, liveness, speechiness,
    duration_ms, key, mode, time_signature
(only those present in the input CSV will be written)
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ma_config.paths import get_spine_root, get_external_data_root


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    if not s:
        return ""
    # Strip accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Normalize ampersands etc.
    s = s.replace("&", " and ")
    # Keep alnum + spaces only
    cleaned_chars = []
    for ch in s:
        if ch.isalnum() or ch.isspace():
            cleaned_chars.append(ch)
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
            f"[build_spine_audio_from_hot100_lyrics_audio_v1] Required column not found. "
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
        raise SystemExit(f"[build_spine_audio_from_hot100_lyrics_audio_v1] Missing core CSV: {core_path}")

    with core_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(
                f"[build_spine_audio_from_hot100_lyrics_audio_v1] Empty or headerless CSV: {core_path}"
            )

        required_fields = ["spine_track_id", "year", "artist", "title"]
        for rf in required_fields:
            if rf not in reader.fieldnames:
                raise SystemExit(
                    f"[build_spine_audio_from_hot100_lyrics_audio_v1] Core CSV missing required field '{rf}' "
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
            f"[build_spine_audio_from_hot100_lyrics_audio_v1] Core index built: "
            f"{len(index)} key entries."
        )
        return index


def open_lyrics_audio_csv(path: Path) -> csv.DictReader:
    """
    Try UTF-8 first, then latin-1 if needed, and return a DictReader.
    """
    try:
        f = path.open("r", newline="", encoding="utf-8")
        reader = csv.DictReader(f)
        # Touch fieldnames to force header read
        _ = reader.fieldnames
        return reader
    except UnicodeDecodeError:
        f = path.open("r", newline="", encoding="latin-1")
        reader = csv.DictReader(f)
        _ = reader.fieldnames
        return reader


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build spine_audio_from_hot100_lyrics_audio_v1.csv from 2000–2023 lyrics+audio dataset."
    )
    spine_root = get_spine_root()
    external_root = get_external_data_root()
    parser.add_argument(
        "--core",
        default=str(spine_root / "spine_core_tracks_v1.csv"),
        help="Core Tier 1 spine CSV (canonical metadata).",
    )
    parser.add_argument(
        "--lyrics-audio",
        default=str(external_root / "lyrics" / "hot_100_lyrics_audio_2000_2023.csv"),
        help="Hot 100 lyrics+audio CSV for 2000–2023.",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "backfill" / "spine_audio_from_hot100_lyrics_audio_v1.csv"),
        help="Output CSV for Hot 100 lyrics+audio backfill.",
    )

    args = parser.parse_args()

    core_path = Path(args.core).expanduser()
    lyrics_path = Path(args.lyrics_audio).expanduser()
    out_path = Path(args.out).expanduser()

    core_index = build_core_index(core_path)

    if not lyrics_path.exists():
        raise SystemExit(
            f"[build_spine_audio_from_hot100_lyrics_audio_v1] Missing lyrics+audio CSV: {lyrics_path}"
        )

    print(
        f"[build_spine_audio_from_hot100_lyrics_audio_v1] "
        f"Loading lyrics+audio dataset from: {lyrics_path}"
    )

    reader = open_lyrics_audio_csv(lyrics_path)
    if not reader.fieldnames:
        raise SystemExit(
            f"[build_spine_audio_from_hot100_lyrics_audio_v1] Empty or headerless CSV: {lyrics_path}"
        )

    fieldnames_la = list(reader.fieldnames)

    # Detect columns
    year_col = pick_column(
        ["year", "Year", "chart_year"],
        fieldnames_la,
        required=True,
    )
    artist_col = pick_column(
        ["band_singer", "artist", "Artist", "performer", "Performer"],
        fieldnames_la,
        required=True,
    )
    title_col = pick_column(
        ["song", "Song", "title", "Title", "titletext", "TitleText"],
        fieldnames_la,
        required=True,
    )

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
        # common variants (we'll accept these if present)
        "tempo_avg",
        "loudness_avg",
        "danceability_avg",
        "energy_avg",
        "valence_avg",
    ]

    # Keep any candidate that exists exactly in the header
    audio_feature_cols: List[str] = [
        c for c in AUDIO_FEATURE_CANDIDATES if c in fieldnames_la
    ]

    # Also pass through Spotify ID if present (optional)
    spotify_id_col = pick_column(
        ["spotify_id", "Spotify_ID", "spotify_track_id", "track_id"],
        fieldnames_la,
        required=False,
    )
    id_cols: List[str] = []
    if spotify_id_col:
        id_cols.append(spotify_id_col)

    print(
        f"[build_spine_audio_from_hot100_lyrics_audio_v1] Using columns: "
        f"year={year_col}, artist={artist_col}, title={title_col}"
    )
    print(
        f"[build_spine_audio_from_hot100_lyrics_audio_v1] Audio features found: {audio_feature_cols}"
    )
    if id_cols:
        print(
            f"[build_spine_audio_from_hot100_lyrics_audio_v1] ID columns included: {id_cols}"
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

        # This dataset is 2000–2023; keep a guard so we don't accidentally
        # match weird out-of-range rows.
        if year < 2000 or year > 2025:
            continue

        artist_norm = normalize_text(row.get(artist_col, ""))
        title_norm = normalize_text(row.get(title_col, ""))
        if not artist_norm or not title_norm:
            continue

        key = (year, artist_norm, title_norm)
        spine_id = core_index.get(key)
        if not spine_id:
            continue

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
            continue

        backfill_by_spine_id[spine_id] = feat
        matched_rows += 1

    print(
        f"[build_spine_audio_from_hot100_lyrics_audio_v1] Lyrics+audio rows scanned: {total_rows}, "
        f"matched to core spine: {matched_rows}, "
        f"unique spine_track_ids with backfill: {len(backfill_by_spine_id)}"
    )

    # Write backfill CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames_out: List[str] = ["spine_track_id"]
    for col in audio_feature_cols + id_cols:
        if col not in fieldnames_out:
            fieldnames_out.append(col)

    print(
        f"[build_spine_audio_from_hot100_lyrics_audio_v1] Writing backfill to: {out_path}"
    )

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
        f"[build_spine_audio_from_hot100_lyrics_audio_v1] Done. "
        f"Wrote {len(backfill_by_spine_id)} rows to {out_path}"
    )


if __name__ == "__main__":
    main()
