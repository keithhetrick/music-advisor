#!/usr/bin/env python3
"""
build_core_1600_seed_billboard.py

Build a "core" Billboard corpus (~1,600 songs: Top N per year) from a
raw Billboard CSV.

This is flexible on column names; you tell it which columns correspond
to year/title/artist/rank via CLI flags.

Typical usage:

    python build_core_1600_seed_billboard.py \
        --in /path/to/billboard_year_end_raw.csv \
        --out /path/to/core_1600_seed_billboard.csv \
        --year-col year \
        --title-col title \
        --artist-col artist \
        --rank-col rank \
        --year-min 1985 \
        --year-max 2024 \
        --top-n 40

Resulting CSV columns:

    year,title,artist,year_end_rank
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Tuple, Any, List


def normalize_key(s: str) -> str:
    """
    Simple normalization for (year, title, artist) keys:
    - strip whitespace
    - lowercase
    """
    return " ".join(s.strip().lower().split())


def build_core_corpus(
    input_path: Path,
    output_path: Path,
    year_col: str,
    title_col: str,
    artist_col: str,
    rank_col: str,
    year_min: int,
    year_max: int,
    top_n: int,
) -> None:
    """
    Read the raw Billboard CSV and produce a core corpus CSV with columns:
      year,title,artist,year_end_rank

    - We keep only rows where year_min <= year <= year_max.
    - We keep only rows where rank <= top_n.
    - If the same (year, title, artist) appears more than once, we keep
      the best (lowest) rank.
    """
    with input_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)

    if not rows:
        raise SystemExit(f"[ERROR] Input CSV {input_path} is empty.")

    # Map (year, norm_title, norm_artist) -> best row dict
    best_by_key: Dict[Tuple[int, str, str], Dict[str, Any]] = {}

    for row in rows:
        # Parse year
        year_raw = row.get(year_col, "").strip()
        try:
            year = int(year_raw)
        except Exception:
            # Skip rows with no usable year
            continue

        if year < year_min or year > year_max:
            continue

        # Parse rank
        rank_raw = row.get(rank_col, "").strip()
        try:
            rank = int(rank_raw)
        except Exception:
            # Skip if rank can't be parsed
            continue

        if rank > top_n:
            continue

        title = row.get(title_col, "").strip()
        artist = row.get(artist_col, "").strip()
        if not title or not artist:
            continue

        norm_title = normalize_key(title)
        norm_artist = normalize_key(artist)
        key = (year, norm_title, norm_artist)

        # If we've seen this song already, keep the best (lowest) rank
        existing = best_by_key.get(key)
        if existing is not None:
            try:
                existing_rank = int(str(existing.get("year_end_rank", existing.get(rank_col, ""))).strip())
            except Exception:
                existing_rank = rank

            if rank >= existing_rank:
                continue  # existing is better or equal

        # Store a normalized row for output
        best_by_key[key] = {
            "year": year,
            "title": title,
            "artist": artist,
            "year_end_rank": rank,
        }

    # Turn dict into sorted list
    core_rows: List[Dict[str, Any]] = list(best_by_key.values())
    core_rows.sort(key=lambda r: (r["year"], r["year_end_rank"]))

    print(f"[INFO] Selected {len(core_rows)} rows for core corpus "
          f"({year_min}-{year_max}, top {top_n} per year).")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["year", "title", "artist", "year_end_rank"]

    with output_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for r in core_rows:
            writer.writerow(r)

    print(f"[OK] Wrote core corpus to {output_path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build a core Billboard corpus (~1,600 songs) from a raw Billboard CSV."
    )
    ap.add_argument(
        "--in",
        dest="input_csv",
        required=True,
        help="Input Billboard CSV path.",
    )
    ap.add_argument(
        "--out",
        dest="output_csv",
        required=True,
        help="Output core corpus CSV path.",
    )
    ap.add_argument(
        "--year-col",
        default="year",
        help="Column name for year (default: year).",
    )
    ap.add_argument(
        "--title-col",
        default="title",
        help="Column name for song title (default: title).",
    )
    ap.add_argument(
        "--artist-col",
        default="artist",
        help="Column name for artist (default: artist).",
    )
    ap.add_argument(
        "--rank-col",
        default="rank",
        help="Column name for year-end rank (default: rank).",
    )
    ap.add_argument(
        "--year-min",
        type=int,
        default=1985,
        help="Minimum year to include (default: 1985).",
    )
    ap.add_argument(
        "--year-max",
        type=int,
        default=2024,
        help="Maximum year to include (default: 2024).",
    )
    ap.add_argument(
        "--top-n",
        type=int,
        default=40,
        help="Top N songs per year to keep (default: 40).",
    )

    args = ap.parse_args()

    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)

    if not input_path.exists():
        raise SystemExit(f"[ERROR] Input CSV not found: {input_path}")

    build_core_corpus(
        input_path=input_path,
        output_path=output_path,
        year_col=args.year_col,
        title_col=args.title_col,
        artist_col=args.artist_col,
        rank_col=args.rank_col,
        year_min=args.year_min,
        year_max=args.year_max,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
