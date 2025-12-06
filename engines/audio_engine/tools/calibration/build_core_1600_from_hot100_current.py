#!/usr/bin/env python3
"""
build_core_1600_from_hot100_current.py

Purpose
-------
Take the UT Austin "hot-100-current.csv" weekly Billboard Hot 100 archive
and collapse it into a year-based "core hit spine" CSV suitable for
Music Advisor's historical echo backbone.

For each year in [year_min, year_max], we:
  - Group rows by (year, title, artist)
  - Aggregate weekly chart performance:
      * best_rank        = min(weekly rank)
      * weeks_on_chart   = count of weeks on chart in that year
      * chart_points     = sum over weeks of points(rank),
                           where points(rank) = max(0, 101 - rank)
  - Rank songs within the year by:
      1) chart_points (descending)
      2) best_rank (ascending)
      3) title (ascending) as a stable tie-breaker
  - Keep top N songs per year (default: 40)

Output
------
Writes a CSV with columns:

  year,title,artist,year_end_rank,best_rank,weeks_on_chart,chart_points

This becomes the input to spotify_enrich_core_corpus.py.

Usage
-----
Example with UT hot-100-current.csv (weekly chart):

  cd ~/music-advisor

  python tools/build_core_1600_from_hot100_current.py \
    --in /path/to/hot-100-current.csv \
    --out /path/to/core_1600_seed_billboard.csv \
    --date-col "CHART DATE" \
    --rank-col "THIS WEEK" \
    --title-col "TITLE" \
    --artist-col "PERFORMER" \
    --year-min 1985 \
    --year-max 2024 \
    --top-n 40

NOTE: Column names are case-insensitive and can be "cleaned" forms
like chart_date/this_week/title/performer. This script normalizes
header names internally, so you don't have to match exact casing.
"""

import argparse
import csv
import datetime
import math
import os
from collections import defaultdict, namedtuple
from typing import Dict, List, Tuple, Optional


def _normalize_name(name: str) -> str:
    """
    Normalize a column name: lowercase, non-alnum -> underscores.
    This lets us match "CHART DATE" to "chart_date", etc.
    """
    if name is None:
        return ""
    name = name.strip()
    out_chars = []
    for ch in name:
        if ch.isalnum():
            out_chars.append(ch.lower())
        else:
            out_chars.append("_")
    # collapse multiple underscores
    out = []
    prev_underscore = False
    for ch in out_chars:
        if ch == "_" and prev_underscore:
            continue
        prev_underscore = (ch == "_")
        out.append(ch)
    return "".join(out).strip("_")


def _build_header_map(fieldnames: List[str]) -> Dict[str, str]:
    """
    Build a mapping from normalized header -> actual header name.

    Example:
      fieldnames = ["CHART DATE", "THIS WEEK", "TITLE", "PERFORMER"]
      returns { "chart_date": "CHART DATE",
                "this_week": "THIS WEEK",
                "title": "TITLE",
                "performer": "PERFORMER" }
    """
    mapping: Dict[str, str] = {}
    for col in fieldnames:
        norm = _normalize_name(col)
        if norm and norm not in mapping:
            mapping[norm] = col
    return mapping


def _resolve_column(fieldnames: List[str], header_map: Dict[str, str], requested: str) -> str:
    """
    Resolve a requested column name to an actual CSV header:

      - If requested matches exactly, use it.
      - Else, normalize requested and look it up in header_map.
      - If still not found, raise a helpful error.
    """
    if requested in fieldnames:
        return requested

    norm_req = _normalize_name(requested)
    if norm_req in header_map:
        return header_map[norm_req]

    # Try direct normalized name against normalized fieldnames
    for fn in fieldnames:
        if _normalize_name(fn) == norm_req:
            return fn

    raise ValueError(
        f"Could not find column matching '{requested}'. "
        f"Available columns: {fieldnames}"
    )


def _parse_date(date_str: str) -> Optional[datetime.date]:
    """
    Try parsing a Billboard chart date from a handful of common formats.

    UT / Billboard data is typically 'YYYY-MM-DD', but we handle a few
    common variations just in case.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d-%b-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    # If all fail, just return None; caller can decide to skip row.
    return None


def _safe_int(val: str) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.upper() == "NA":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _rank_to_points(rank: int) -> int:
    """
    Simple chart points: #1 -> 100, #2 -> 99, ..., #100 -> 1, >100 -> 0.
    """
    if rank is None:
        return 0
    if rank <= 0:
        return 0
    if rank > 100:
        return 0
    return max(0, 101 - rank)


AggRow = namedtuple(
    "AggRow",
    ["year", "title", "artist", "best_rank", "weeks_on_chart", "chart_points"],
)


def build_core_spine(
    in_path: str,
    out_path: str,
    date_col_raw: str,
    rank_col_raw: str,
    title_col_raw: str,
    artist_col_raw: str,
    year_min: int,
    year_max: int,
    top_n: int,
) -> None:
    """
    Main aggregation function.
    """

    if not os.path.exists(in_path):
        raise FileNotFoundError(f"Input CSV not found: {in_path}")

    print(f"[INFO] Reading weekly Hot 100 data from {in_path}")

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV {in_path} has no header / is empty.")

        fieldnames = reader.fieldnames
        header_map = _build_header_map(fieldnames)

        # Resolve actual header names from requested names
        date_col = _resolve_column(fieldnames, header_map, date_col_raw)
        rank_col = _resolve_column(fieldnames, header_map, rank_col_raw)
        title_col = _resolve_column(fieldnames, header_map, title_col_raw)
        artist_col = _resolve_column(fieldnames, header_map, artist_col_raw)

        print("[INFO] Resolved columns:")
        print(f"       date_col   -> {date_col}")
        print(f"       rank_col   -> {rank_col}")
        print(f"       title_col  -> {title_col}")
        print(f"       artist_col -> {artist_col}")

        # Aggregation key: (year, title_norm, artist_norm)
        agg: Dict[Tuple[int, str, str], AggRow] = {}

        row_count = 0
        used_rows = 0
        skipped_bad_date = 0
        skipped_out_of_range = 0

        for row in reader:
            row_count += 1
            date_raw = row.get(date_col, "")
            dt = _parse_date(date_raw)
            if dt is None:
                skipped_bad_date += 1
                continue

            year = dt.year
            if year < year_min or year > year_max:
                skipped_out_of_range += 1
                continue

            rank = _safe_int(row.get(rank_col))
            if rank is None:
                # skip rows with no valid rank
                continue

            title = (row.get(title_col) or "").strip()
            artist = (row.get(artist_col) or "").strip()
            if not title or not artist:
                continue

            title_norm = title.lower()
            artist_norm = artist.lower()

            key = (year, title_norm, artist_norm)
            points = _rank_to_points(rank)

            if key not in agg:
                agg[key] = AggRow(
                    year=year,
                    title=title,
                    artist=artist,
                    best_rank=rank,
                    weeks_on_chart=1,
                    chart_points=points,
                )
            else:
                prev = agg[key]
                best_rank = min(prev.best_rank, rank)
                weeks_on_chart = prev.weeks_on_chart + 1
                chart_points = prev.chart_points + points
                agg[key] = AggRow(
                    year=year,
                    title=prev.title,   # keep first seen spelling
                    artist=prev.artist,
                    best_rank=best_rank,
                    weeks_on_chart=weeks_on_chart,
                    chart_points=chart_points,
                )

            used_rows += 1

    print(f"[INFO] Processed {row_count} rows.")
    print(f"[INFO] Used {used_rows} rows after basic filtering.")
    if skipped_bad_date:
        print(f"[WARN] Skipped {skipped_bad_date} rows with unparseable dates.")
    if skipped_out_of_range:
        print(f"[INFO] Skipped {skipped_out_of_range} rows outside {year_min}-{year_max}.")

    # Organize by year
    by_year: Dict[int, List[AggRow]] = defaultdict(list)
    for row in agg.values():
        by_year[row.year].append(row)

    print(f"[INFO] Aggregated to {len(agg)} unique (year, title, artist) entries "
          f"across {len(by_year)} years.")

    # Prepare output
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(
            [
                "year",
                "title",
                "artist",
                "year_end_rank",
                "best_rank",
                "weeks_on_chart",
                "chart_points",
            ]
        )

        total_written = 0
        for year in sorted(by_year.keys()):
            rows = by_year[year]

            # sort within year: points desc, best_rank asc, title asc
            rows_sorted = sorted(
                rows,
                key=lambda r: (-r.chart_points, r.best_rank, r.title.lower()),
            )

            # keep only top N
            top_rows = rows_sorted[:top_n]

            print(
                f"[INFO] Year {year}: {len(rows)} candidates, keeping top {len(top_rows)}"
            )

            for idx, r in enumerate(top_rows, start=1):
                writer.writerow(
                    [
                        year,
                        r.title,
                        r.artist,
                        idx,  # year_end_rank within this year
                        r.best_rank,
                        r.weeks_on_chart,
                        r.chart_points,
                    ]
                )
                total_written += 1

    print(f"[DONE] Wrote {total_written} rows to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a core year-based Billboard hit spine from weekly Hot 100 data."
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        required=True,
        help="Input weekly Hot 100 CSV (e.g., /path/to/hot-100-current.csv).",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        required=True,
        help="Output core spine CSV (e.g., /path/to/core_1600_seed_billboard.csv).",
    )
    parser.add_argument(
        "--date-col",
        dest="date_col",
        default="chart_date",
        help="Name of the chart date column (e.g., 'CHART DATE' or 'chart_date').",
    )
    parser.add_argument(
        "--rank-col",
        dest="rank_col",
        default="this_week",
        help="Name of the weekly rank column (e.g., 'THIS WEEK' or 'this_week').",
    )
    parser.add_argument(
        "--title-col",
        dest="title_col",
        default="title",
        help="Name of the song title column (e.g., 'TITLE' or 'title').",
    )
    parser.add_argument(
        "--artist-col",
        dest="artist_col",
        default="performer",
        help="Name of the artist column (e.g., 'PERFORMER' or 'performer').",
    )
    parser.add_argument(
        "--year-min",
        type=int,
        default=1985,
        help="Minimum year to include (default: 1985).",
    )
    parser.add_argument(
        "--year-max",
        type=int,
        default=2024,
        help="Maximum year to include (default: 2024).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=40,
        help="Number of songs to keep per year (default: 40).",
    )

    args = parser.parse_args()

    build_core_spine(
        in_path=args.in_path,
        out_path=args.out_path,
        date_col_raw=args.date_col,
        rank_col_raw=args.rank_col,
        title_col_raw=args.title_col,
        artist_col_raw=args.artist_col,
        year_min=args.year_min,
        year_max=args.year_max,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
