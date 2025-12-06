#!/usr/bin/env python3
"""
build_yearend_hot100_top100_from_weekly_v1.py

Merge an existing Year-End Top 100 CSV (e.g., liquidgenius through 2021)
with a derived Year-End Top 100 for missing years (2022–2024) computed
from weekly UT Hot 100 data.

Derivation (weekly):
- Input: data/private/local_assets/external/weekly/ut_hot_100_1958_present.csv
- For each year in target range, accumulate points per (title, artist)
  as sum(101 - weekly_rank) where weekly_rank is the `current_week` column.
  Higher points = better rank. Deterministic tie-breaker: higher weeks_on_chart,
  then lower peak_pos, then lexical slug.
- Select top 100 per year, assign yearend_rank 1..N.

Outputs:
- data/private/local_assets/yearend_hot100/yearend_hot100_top100_1985_2024.csv
  Columns: year, yearend_rank, title, artist

Notes:
- Keeps existing rows from the base CSV for years before derived_range_start.
- Only fills/overwrites years in derived_range (default 2022–2024).
- No Spotify IDs are added here; downstream Tier 2 core builder will handle slugs.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.spine.spine_slug import make_spine_slug
from shared.config.paths import (
    get_external_data_root,
    get_yearend_hot100_top100_path,
)

BASE_INPUT_DEFAULT = str(get_external_data_root() / "year_end/year_end_hot_100_liquidgenius_1946_2024.csv")
WEEKLY_INPUT_DEFAULT = str(get_external_data_root() / "weekly/ut_hot_100_1958_present.csv")
OUTPUT_DEFAULT = str(get_yearend_hot100_top100_path())


@dataclass
class YearEndRow:
    year: int
    rank: int
    title: str
    artist: str


def load_base_rows(path: Path, year_min: int, year_max: int, derived_range: Tuple[int, int]) -> List[YearEndRow]:
    """
    Load existing year-end rows, keeping only years not in derived_range.
    """
    rows: List[YearEndRow] = []
    if not path.is_file():
        print(f"[WARN] Base CSV not found at {path}; skipping base merge.")
        return rows

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rank_col = next((c for c in ["yearend_rank", "year_end_rank", "rank", "No."] if c in fields), None)
        title_col = next((c for c in ["title", "Title", "song"] if c in fields), None)
        artist_col = next((c for c in ["artist", "Artist", "Artist(s)", "artists"] if c in fields), None)
        if rank_col is None or title_col is None or artist_col is None:
            raise SystemExit(f"[ERROR] Base CSV {path} missing required columns. Found: {fields}")

        for raw in reader:
            try:
                year = int((raw.get("year") or raw.get("Year") or "").strip())
            except Exception:
                continue
            if year < year_min or year > year_max:
                continue
            # Skip years we will overwrite from weekly-derived range
            if derived_range[0] <= year <= derived_range[1]:
                continue
            try:
                rank = int((raw.get(rank_col) or "").strip())
            except Exception:
                continue
            title = (raw.get(title_col) or "").strip()
            artist = (raw.get(artist_col) or "").strip()
            if not title or not artist:
                continue
            rows.append(YearEndRow(year=year, rank=rank, title=title, artist=artist))
    return rows


def derive_from_weekly(path: Path, year_min: int, year_max: int) -> List[YearEndRow]:
    """
    Compute year-end Top 100 per year using chart points from weekly Hot 100:
    points = 101 - current_week_rank.
    """
    if not path.is_file():
        raise SystemExit(f"[ERROR] Weekly CSV not found: {path}")

    @dataclass
    class Agg:
        points: float
        weeks: int
        peak: int
        title: str
        artist: str

    per_year: Dict[int, Dict[str, Agg]] = defaultdict(dict)  # year -> slug -> Agg

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            chart_week = raw.get("chart_week") or ""
            try:
                year = datetime.strptime(chart_week[:10], "%Y-%m-%d").year
            except Exception:
                continue
            if year < year_min or year > year_max:
                continue

            title = (raw.get("title") or "").strip()
            artist = (raw.get("performer") or raw.get("artist") or "").strip()
            if not title or not artist:
                continue
            slug = make_spine_slug(title, artist)

            rank_raw = raw.get("current_week") or raw.get("rank") or raw.get("current_week_rank")
            try:
                rank = int(rank_raw)
            except Exception:
                continue
            if rank < 1 or rank > 100:
                continue

            points = 101 - rank
            weeks_on_chart = raw.get("wks_on_chart") or raw.get("weeks_on_chart") or ""
            try:
                weeks = int(weeks_on_chart)
            except Exception:
                weeks = 0
            peak_raw = raw.get("peak_pos") or raw.get("peak_rank") or ""
            try:
                peak = int(peak_raw)
            except Exception:
                peak = rank  # fallback to current rank if missing

            agg = per_year[year].get(slug)
            if agg is None:
                per_year[year][slug] = Agg(points=points, weeks=1, peak=peak, title=title, artist=artist)
            else:
                agg.points += points
                agg.weeks += 1
                agg.peak = min(agg.peak, peak)

    derived_rows: List[YearEndRow] = []
    for year, slug_map in per_year.items():
        ranked = sorted(
            slug_map.values(),
            key=lambda a: (-a.points, -a.weeks, a.peak, make_spine_slug(a.title, a.artist)),
        )
        for idx, agg in enumerate(ranked[:100], start=1):
            derived_rows.append(YearEndRow(year=year, rank=idx, title=agg.title, artist=agg.artist))
    return derived_rows


def write_output(path: Path, rows: List[YearEndRow]) -> None:
    fieldnames = ["year", "yearend_rank", "title", "artist"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in sorted(rows, key=lambda x: (x.year, x.rank)):
            writer.writerow({"year": r.year, "yearend_rank": r.rank, "title": r.title, "artist": r.artist})


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Year-End Hot 100 Top 100 (1985–2024) with derived 2022–2024 from weekly data.")
    parser.add_argument("--base-csv", default=BASE_INPUT_DEFAULT, help="Existing Year-End Top 100 CSV (used for years outside derived range)")
    parser.add_argument("--weekly-csv", default=WEEKLY_INPUT_DEFAULT, help="Weekly UT Hot 100 CSV")
    parser.add_argument("--out", default=OUTPUT_DEFAULT, help="Output merged Year-End Top 100 CSV")
    parser.add_argument("--year-min", type=int, default=1985, help="Minimum year to include")
    parser.add_argument("--year-max", type=int, default=2024, help="Maximum year to include")
    parser.add_argument("--derived-year-min", type=int, default=2022, help="First year to derive from weekly data")
    parser.add_argument("--derived-year-max", type=int, default=2024, help="Last year to derive from weekly data")
    args = parser.parse_args()

    base_path = Path(args.base_csv)
    weekly_path = Path(args.weekly_csv)
    out_path = Path(args.out)

    print(f"[INFO] Loading base Year-End CSV from {base_path} ...")
    base_rows = load_base_rows(base_path, args.year_min, args.year_max, (args.derived_year_min, args.derived_year_max))
    print(f"[INFO] Loaded {len(base_rows)} base rows (excluding derived years)")

    print(f"[INFO] Deriving Year-End ranks from weekly data {weekly_path} for {args.derived_year_min}-{args.derived_year_max} ...")
    derived_rows = derive_from_weekly(weekly_path, args.derived_year_min, args.derived_year_max)
    print(f"[INFO] Derived {len(derived_rows)} rows from weekly data")

    all_rows = [r for r in base_rows if args.year_min <= r.year <= args.year_max] + [
        r for r in derived_rows if args.year_min <= r.year <= args.year_max
    ]
    write_output(out_path, all_rows)
    print(f"[INFO] Wrote merged Year-End Top 100 to {out_path} with {len(all_rows)} rows")


if __name__ == "__main__":
    main()
