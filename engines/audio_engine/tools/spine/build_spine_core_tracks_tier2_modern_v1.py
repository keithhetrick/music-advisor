#!/usr/bin/env python3
"""
Build Tier 2 core spine CSV for Modern Year-End Hot 100 Top 100 (1985–2024).
Env-driven paths via ma_config (MA_SPINE_ROOT / MA_DATA_ROOT).
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_spine_root, get_data_root
from shared.config.paths import get_yearend_hot100_top100_path
from tools.spine.spine_slug import make_spine_slug

ensure_repo_root()

CHART_DEFAULT = "hot_100_year_end"
TIER_LABEL = "EchoTier_2_YearEnd_Top100_Modern"
SOURCE_CHART = "yearend_hot100_top100"
BILLBOARD_SOURCE = "YearEnd_Hot100_Top100"


@dataclass
class CoreRow:
    spine_track_id: str
    year: int
    year_end_rank: int
    title: str
    artist: str
    chart: str
    echo_tier: str
    source: str
    slug: str
    spotify_id: str = ""


def normalize_text(s: str) -> str:
    return " ".join((s or "").strip().split())


def parse_row(row: dict, year_col: str, rank_col: str, title_col: str, artist_col: str, spotify_col: str) -> Optional[CoreRow]:
    try:
        year = int(row.get(year_col, ""))
        rank = int(row.get(rank_col, ""))
    except Exception:
        return None
    title = normalize_text(row.get(title_col, ""))
    artist = normalize_text(row.get(artist_col, ""))
    if not title or not artist or year < 1900:
        return None
    slug = make_spine_slug(title, artist)
    spotify_id = row.get(spotify_col, "") if spotify_col in row else ""
    return CoreRow(
        spine_track_id=f"{SOURCE_CHART}_{year}_{rank}",
        year=year,
        year_end_rank=rank,
        title=title,
        artist=artist,
        chart=CHART_DEFAULT,
        echo_tier=TIER_LABEL,
        source=BILLBOARD_SOURCE,
        slug=slug,
        spotify_id=spotify_id,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Tier 2 core spine CSV for modern year-end Hot 100 Top 100.")
    data_root = get_data_root()
    spine_root = get_spine_root()
    parser.add_argument(
        "--yearend-csv",
        default=str(get_yearend_hot100_top100_path()),
        help="Year-End Top 100 CSV (1985–2024).",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "spine_core_tracks_tier2_modern_v1.csv"),
        help="Output Tier 2 core spine CSV.",
    )
    parser.add_argument("--year-col", default="year", help="Column name for chart year.")
    parser.add_argument("--rank-col", default="yearend_rank", help="Column name for rank/position.")
    parser.add_argument("--title-col", default="title", help="Column name for song title.")
    parser.add_argument("--artist-col", default="artist", help="Column name for artist.")
    parser.add_argument("--spotify-col", default="spotify_id", help="Optional Spotify ID column name.")
    args = parser.parse_args()

    src_path = Path(args.yearend_csv).expanduser()
    out_path = Path(args.out).expanduser()

    if not src_path.exists():
        raise SystemExit(f"[ERROR] Year-end CSV not found: {src_path}")

    rows: List[CoreRow] = []
    with src_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = parse_row(
                row,
                year_col=args.year_col,
                rank_col=args.rank_col,
                title_col=args.title_col,
                artist_col=args.artist_col,
                spotify_col=args.spotify_col,
            )
            if parsed:
                rows.append(parsed)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "spine_track_id",
        "year",
        "year_end_rank",
        "title",
        "artist",
        "chart",
        "echo_tier",
        "source",
        "slug",
        "spotify_id",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r.__dict__)

    print(f"[DONE] Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
