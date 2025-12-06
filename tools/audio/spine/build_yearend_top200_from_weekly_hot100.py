#!/usr/bin/env python3
"""
build_yearend_top200_from_weekly_hot100.py

Derive a Year-End Hot 100 "Top 200" list per year (1985–2024 default)
from weekly Hot 100 data (e.g., data/private/local_assets/external/weekly/ut_hot_100_1958_present.csv).

Notes:
- This is a reproducible, offline approximation (points-based), not an official Billboard list.
- Scoring: weekly_score = 101 - rank (rank 1 => 100 pts, rank 100 => 1 pt).
  Per-year total score = sum of weekly_score across the calendar year.
- Output is a simple Year-End CSV usable as input to Tier 3 builder.

Output columns:
  year, yearend_rank, title, artist, score, weeks_on_chart, peak_rank, source

Tier 1/2 behavior and files remain untouched.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Allow running as script by adding repo root to sys.path
from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

# Local slug helper (matches Tier 1/2 spine logic)
from tools.spine.spine_slug import make_spine_slug
from shared.config.paths import get_external_data_root, get_yearend_hot100_top200_path


@dataclass
class AggRow:
    year: int
    title: str
    artist: str
    slug: str
    total_score: float
    weeks: int
    peak_rank: int


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build Year-End Top 200 (points-based) from weekly Hot 100 data."
    )
    p.add_argument(
        "--weekly-csv",
        default=str(get_external_data_root() / "weekly/ut_hot_100_1958_present.csv"),
        help="Weekly Hot 100 CSV with columns: chart_week, current_week, title, performer, last_week, peak_pos, wks_on_chart.",
    )
    p.add_argument(
        "--out",
        default=str(get_yearend_hot100_top200_path()),
        help="Output Year-End Top 200 CSV.",
    )
    p.add_argument(
        "--year-min",
        type=int,
        default=1985,
        help="Minimum year to include.",
    )
    p.add_argument(
        "--year-max",
        type=int,
        default=2024,
        help="Maximum year to include.",
    )
    p.add_argument(
        "--top-n",
        type=int,
        default=200,
        help="Number of tracks to keep per year.",
    )
    return p.parse_args()


def load_weekly_rows(path: Path, year_min: int, year_max: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            week_str = (raw.get("chart_week") or "").strip()
            try:
                year_val = datetime.fromisoformat(week_str).year
            except Exception:
                # fallback for m/d/Y formats seen in other weekly files
                try:
                    year_val = datetime.strptime(week_str, "%m/%d/%Y").year
                except Exception:
                    continue
            if year_val < year_min or year_val > year_max:
                continue

            rank_str = (raw.get("current_week") or raw.get("Week Position") or "").strip()
            try:
                rank = int(rank_str)
            except ValueError:
                continue
            if rank < 1 or rank > 100:
                continue

            title = (raw.get("title") or raw.get("Song") or "").strip()
            artist = (raw.get("performer") or raw.get("Performer") or "").strip()
            if not title or not artist:
                continue

            peak_str = (raw.get("peak_pos") or raw.get("Peak Position") or "").strip()
            try:
                peak = int(peak_str)
            except ValueError:
                peak = rank

            rows.append(
                {
                    "year": year_val,
                    "rank": rank,
                    "title": title,
                    "artist": artist,
                    "peak": peak,
                }
            )
    return rows


def aggregate_year_end(rows: List[Dict[str, str]]) -> Dict[int, List[AggRow]]:
    agg: Dict[Tuple[int, str], AggRow] = {}
    for r in rows:
        year = r["year"]
        rank = r["rank"]
        title = r["title"]
        artist = r["artist"]
        peak = r["peak"]
        slug = make_spine_slug(title, artist)
        key = (year, slug)
        score = 101 - rank  # simple inverse-rank points

        if key not in agg:
            agg[key] = AggRow(
                year=year,
                title=title,
                artist=artist,
                slug=slug,
                total_score=0.0,
                weeks=0,
                peak_rank=peak,
            )
        row = agg[key]
        row.total_score += score
        row.weeks += 1
        if peak < row.peak_rank:
            row.peak_rank = peak

    by_year: Dict[int, List[AggRow]] = defaultdict(list)
    for (year, _slug), row in agg.items():
        by_year[year].append(row)
    return by_year


def write_year_end(out_path: Path, by_year: Dict[int, List[AggRow]], top_n: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["year", "yearend_rank", "title", "artist", "score", "weeks_on_chart", "peak_rank", "source"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        total_rows = 0
        for year in sorted(by_year.keys()):
            rows = by_year[year]
            rows.sort(key=lambda r: (-r.total_score, r.peak_rank, r.title.lower()))
            for idx, r in enumerate(rows[:top_n], start=1):
                writer.writerow(
                    {
                        "year": year,
                        "yearend_rank": idx,
                        "title": r.title,
                        "artist": r.artist,
                        "score": f"{r.total_score:.3f}",
                        "weeks_on_chart": r.weeks,
                        "peak_rank": r.peak_rank,
                        "source": "ut_hot_100_1958_present_points",
                    }
                )
                total_rows += 1
        print(f"[INFO] Wrote {total_rows} rows to {out_path}")


def main() -> None:
    args = parse_args()
    weekly_path = Path(args.weekly_csv)
    out_path = Path(args.out)

    print(f"[INFO] Loading weekly Hot 100 from {weekly_path} ...")
    rows = load_weekly_rows(weekly_path, args.year_min, args.year_max)
    print(f"[INFO] Loaded {len(rows)} weekly rows within {args.year_min}-{args.year_max}")

    by_year = aggregate_year_end(rows)
    print(f"[INFO] Aggregated into {len(by_year)} year buckets.")

    write_year_end(out_path, by_year, args.top_n)

    # quick per-year counts
    for year in sorted(by_year.keys()):
        count = min(len(by_year[year]), args.top_n)
        print(f"[INFO] Year {year}: wrote {count} rows")


if __name__ == "__main__":
    main()
