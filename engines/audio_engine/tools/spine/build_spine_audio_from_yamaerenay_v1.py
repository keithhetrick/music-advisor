#!/usr/bin/env python3
"""
Stub: probe coverage of spotify_dataset_19212020_600k_tracks_yamaerenay for Tier 1 spine.

Reads the local 600k-track Spotify features dump, normalizes (year, artist, title),
and reports how many Tier 1 spine tracks can be matched.

This script only prints stats — it does NOT write a backfill CSV yet.
"""

from __future__ import annotations

import argparse
import ast
import csv
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ma_config.paths import get_spine_root, get_external_data_root


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("&", " and ")
    cleaned_chars = []
    for ch in s:
        if ch.isalnum() or ch.isspace():
            cleaned_chars.append(ch)
    s = "".join(cleaned_chars)
    s = " ".join(s.split())
    return s


def extract_year(raw: str) -> Optional[int]:
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    if raw.isdigit() and len(raw) == 4:
        year = int(raw)
        if 1900 <= year <= 2100:
            return year
    m = re.search(r"(19|20)\d{2}", raw)
    if m:
        year = int(m.group(0))
        if 1900 <= year <= 2100:
            return year
    return None


def pick_column(candidates: Iterable[str], fieldnames: List[str]) -> Optional[str]:
    lower_map = {f.lower(): f for f in fieldnames}
    for cand in candidates:
        c_lower = cand.lower()
        if c_lower in lower_map:
            return lower_map[c_lower]
    return None


def build_core_index(core_path: Path) -> Dict[Tuple[int, str, str], str]:
    if not core_path.exists():
        raise SystemExit(f"[build_spine_audio_from_yamaerenay_v1] Missing core CSV: {core_path}")

    with core_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(
                f"[build_spine_audio_from_yamaerenay_v1] Empty or headerless CSV: {core_path}"
            )
        required_fields = ["spine_track_id", "year", "artist", "title"]
        for rf in required_fields:
            if rf not in reader.fieldnames:
                raise SystemExit(
                    f"[build_spine_audio_from_yamaerenay_v1] Core CSV missing required field '{rf}' "
                    f"in {core_path}"
                )

        index: Dict[Tuple[int, str, str], str] = {}
        for row in reader:
            spine_id = (row.get("spine_track_id") or "").strip()
            year_str = (row.get("year") or "").strip()
            if not spine_id or not year_str:
                continue
            try:
                year = int(year_str)
            except ValueError:
                continue
            artist_norm = normalize_text(row.get("artist", ""))
            title_norm = normalize_text(row.get("title", ""))
            if not artist_norm or not title_norm:
                continue
            index[(year, artist_norm, title_norm)] = spine_id
        print(f"[build_spine_audio_from_yamaerenay_v1] Core index built: {len(index)} entries.")
        return index


def normalize_artist_field(raw: str) -> str:
    """
    Artists column often looks like "['Artist1', 'Artist2']".
    Take the first artist after light parsing.
    """
    if not raw:
        return ""
    raw = str(raw).strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list) and parsed:
                return normalize_text(parsed[0])
        except Exception:
            pass
    for sep in [";", ",", "/", "|", " feat ", " featuring "]:
        if sep in raw:
            return normalize_text(raw.split(sep)[0])
    return normalize_text(raw)


def open_tracks_csv(path: Path) -> csv.DictReader:
    try:
        f = path.open("r", newline="", encoding="utf-8")
        reader = csv.DictReader(f)
        _ = reader.fieldnames
        return reader
    except UnicodeDecodeError:
        f = path.open("r", newline="", encoding="latin-1")
        reader = csv.DictReader(f)
        _ = reader.fieldnames
        return reader


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe Tier 1 coverage inside spotify_dataset_19212020_600k_tracks_yamaerenay."
    )
    spine_root = get_spine_root()
    ext_root = get_external_data_root()
    parser.add_argument(
        "--core",
        default=str(spine_root / "spine_core_tracks_v1.csv"),
        help="Core Tier 1 spine CSV (canonical).",
    )
    parser.add_argument(
        "--tracks",
        default=str(ext_root / "weekly" / "spotify_dataset_19212020_600k_tracks_yamaerenay" / "tracks.csv"),
        help="Yamaerenay 600k Spotify tracks CSV.",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        help="Optional minimum year filter on the external dataset.",
    )
    parser.add_argument(
        "--max-year",
        type=int,
        help="Optional maximum year filter on the external dataset.",
    )
    parser.add_argument(
        "--sample-out",
        help="Optional path to write a small CSV of matched rows (artist/title/year + spine_track_id).",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50,
        help="How many matched rows to write if --sample-out is set.",
    )
    args = parser.parse_args()

    core_index = build_core_index(Path(args.core).expanduser())

    tracks_path = Path(args.tracks).expanduser()
    if not tracks_path.exists():
        raise SystemExit(f"[build_spine_audio_from_yamaerenay_v1] Missing tracks CSV: {tracks_path}")

    reader = open_tracks_csv(tracks_path)
    if not reader.fieldnames:
        raise SystemExit(f"[build_spine_audio_from_yamaerenay_v1] Headerless CSV: {tracks_path}")

    fieldnames = list(reader.fieldnames)
    title_col = pick_column(["name", "title", "track_name"], fieldnames)
    artist_col = pick_column(["artists", "artist"], fieldnames)
    year_col = pick_column(["year", "release_date", "release_year"], fieldnames)

    if not (title_col and artist_col and year_col):
        raise SystemExit(
            "[build_spine_audio_from_yamaerenay_v1] Could not find required columns "
            f"(artist/title/year). Headers: {fieldnames}"
        )

    total_rows = 0
    usable_rows = 0
    matches = 0
    matched_spine_ids = set()
    year_values: List[int] = []
    sample_rows: List[Dict[str, str]] = []

    for row in reader:
        total_rows += 1
        year = extract_year(row.get(year_col, ""))
        if not year:
            continue
        if args.min_year and year < args.min_year:
            continue
        if args.max_year and year > args.max_year:
            continue
        artist_norm = normalize_artist_field(row.get(artist_col, ""))
        title_norm = normalize_text(row.get(title_col, ""))
        if not artist_norm or not title_norm:
            continue

        usable_rows += 1
        year_values.append(year)

        key = (year, artist_norm, title_norm)
        spine_id = core_index.get(key)
        if spine_id:
            matches += 1
            matched_spine_ids.add(spine_id)
            if args.sample_out and len(sample_rows) < args.sample_size:
                sample_rows.append(
                    {
                        "spine_track_id": spine_id,
                        "year": str(year),
                        "artist": artist_norm,
                        "title": title_norm,
                    }
                )

    print("[build_spine_audio_from_yamaerenay_v1] --- summary ---")
    print(f"rows processed: {total_rows}")
    print(f"rows with year+artist+title: {usable_rows}")
    print(f"year range (usable rows): {min(year_values) if year_values else '?'} – {max(year_values) if year_values else '?'}")
    print(f"spine matches: {matches} (unique spine IDs: {len(matched_spine_ids)})")
    if matches == 0:
        print("No matches found yet — may need stronger normalization or a filtered subset.")
    else:
        print("Next: add column mapping for audio features and write a backfill CSV.")
        if args.sample_out and sample_rows:
            out_path = Path(args.sample_out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["spine_track_id", "year", "artist", "title"])
                writer.writeheader()
                writer.writerows(sample_rows)
            print(f"Sampled {len(sample_rows)} matches → {out_path}")


if __name__ == "__main__":
    main()
