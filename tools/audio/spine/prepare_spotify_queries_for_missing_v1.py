#!/usr/bin/env python3
"""
Prepare Spotify search queries for Tier 1 spine tracks that still lack audio.

Inputs:
    - data/public/spine/reports/spine_missing_audio_v1.csv
        (from report_spine_missing_audio_v1.py)

Outputs:
    - data/public/spine/reports/spine_missing_audio_spotify_queries_v1.csv

Columns:
    spine_track_id
    year
    year_end_rank
    artist
    title
    chart
    echo_tier
    search_query_basic        -> "Artist - Title"
    search_query_spotify_cli  -> 'track:"Title" artist:"Artist" year:YYYY'
    spotify_search_url        -> https://open.spotify.com/search/<encoded>

Use:
    python tools/spine/prepare_spotify_queries_for_missing_v1.py \
      --min-year 2021 --max-year 2024
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from shared.config.paths import get_spine_root

SPINE_ROOT = get_spine_root()

MISSING_PATH_DEFAULT = SPINE_ROOT / "reports" / "spine_missing_audio_v1.csv"
OUT_PATH_DEFAULT = SPINE_ROOT / "reports" / "spine_missing_audio_spotify_queries_v1.csv"


def safe_int(val: str) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def build_queries(row: Dict[str, str]) -> Dict[str, str]:
    artist = (row.get("artist") or "").strip()
    title = (row.get("title") or "").strip()
    year_str = (row.get("year") or "").strip()
    year = safe_int(year_str)

    basic = f"{artist} - {title}".strip(" -")

    # Spotify-style CLI / API query
    # e.g., track:"Blinding Lights" artist:"The Weeknd" year:2020
    parts: List[str] = []
    if title:
        parts.append(f'track:"{title}"')
    if artist:
        parts.append(f'artist:"{artist}"')
    if year is not None:
        parts.append(f"year:{year}")
    spotify_cli = " ".join(parts)

    # Web search URL for open.spotify.com (manual inspection)
    # We'll use a looser string for search
    search_string = basic
    if year is not None:
        search_string = f"{basic} year:{year}".strip()
    spotify_url = "https://open.spotify.com/search/" + quote_plus(search_string)

    return {
        "search_query_basic": basic,
        "search_query_spotify_cli": spotify_cli,
        "spotify_search_url": spotify_url,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare Spotify search queries for missing Tier 1 audio tracks."
    )
    parser.add_argument(
        "--missing",
        default=str(MISSING_PATH_DEFAULT),
        help=f"CSV of missing audio tracks (default: {MISSING_PATH_DEFAULT})",
    )
    parser.add_argument(
        "--out",
        default=str(OUT_PATH_DEFAULT),
        help=f"Output CSV for Spotify queries (default: {OUT_PATH_DEFAULT})",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=None,
        help="Minimum year to include (e.g., 2021).",
    )
    parser.add_argument(
        "--max-year",
        type=int,
        default=None,
        help="Maximum year to include (e.g., 2024).",
    )

    args = parser.parse_args()

    missing_path = Path(args.missing)
    out_path = Path(args.out)

    if not missing_path.exists():
        raise SystemExit(
            f"[prepare_spotify_queries_for_missing_v1] Missing input CSV: {missing_path}"
        )

    with missing_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        if not reader.fieldnames:
            raise SystemExit(
                f"[prepare_spotify_queries_for_missing_v1] No header in: {missing_path}"
            )

        required_fields = [
            "spine_track_id",
            "year",
            "year_end_rank",
            "artist",
            "title",
            "chart",
            "echo_tier",
        ]
        for rf in required_fields:
            if rf not in reader.fieldnames:
                raise SystemExit(
                    f"[prepare_spotify_queries_for_missing_v1] Required field '{rf}' "
                    f"not found in header: {reader.fieldnames}"
                )

        rows_in: List[Dict[str, str]] = []
        for row in reader:
            year = safe_int(row.get("year"))
            if args.min_year is not None and (year is None or year < args.min_year):
                continue
            if args.max_year is not None and (year is None or year > args.max_year):
                continue
            rows_in.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames_out = [
        "spine_track_id",
        "year",
        "year_end_rank",
        "artist",
        "title",
        "chart",
        "echo_tier",
        "search_query_basic",
        "search_query_spotify_cli",
        "spotify_search_url",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames_out)
        writer.writeheader()

        for row in rows_in:
            q = build_queries(row)
            out_row = {
                "spine_track_id": row.get("spine_track_id", ""),
                "year": row.get("year", ""),
                "year_end_rank": row.get("year_end_rank", ""),
                "artist": row.get("artist", ""),
                "title": row.get("title", ""),
                "chart": row.get("chart", ""),
                "echo_tier": row.get("echo_tier", ""),
                "search_query_basic": q["search_query_basic"],
                "search_query_spotify_cli": q["search_query_spotify_cli"],
                "spotify_search_url": q["spotify_search_url"],
            }
            writer.writerow(out_row)

    print(
        f"[prepare_spotify_queries_for_missing_v1] Wrote {len(rows_in)} rows to {out_path}"
    )
    if args.min_year or args.max_year:
        print(
            f"[prepare_spotify_queries_for_missing_v1] Year filter: "
            f"{args.min_year or '-inf'}–{args.max_year or '+inf'}"
        )


if __name__ == "__main__":
    main()
