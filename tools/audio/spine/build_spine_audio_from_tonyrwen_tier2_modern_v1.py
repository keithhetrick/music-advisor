#!/usr/bin/env python3
"""
build_spine_audio_from_tonyrwen_tier2_modern_v1.py

Map tonyrwen Year-End Top 100 features (1970–2020) onto the Tier 2 core spine
(1985–2024), producing a spine_track_id-aligned audio CSV for backfill.

Output:
  data/public/spine/backfill/spine_audio_from_tonyrwen_tier2_modern_v1.csv

Notes:
  - Uses primary_dataset.csv (includes rank, title, artist, Spotify id, features).
  - Tier 1 files/behavior are untouched.
  - Coverage limited to tonyrwen years (<=2020); 2021–2024 will remain unmatched.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.spine.spine_slug import make_spine_slug
from shared.config.paths import get_external_data_root, get_spine_root


@dataclass
class SpineRow:
    spine_track_id: str
    year: int
    title: str
    artist: str


def load_spine_core(path: Path) -> Dict[Tuple[int, str], SpineRow]:
    if not path.exists():
        raise SystemExit(f"[ERROR] Spine core not found: {path}")
    mapping: Dict[Tuple[int, str], SpineRow] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get("spine_track_id") or ""
            title = row.get("title") or ""
            artist = row.get("artist") or ""
            year_raw = row.get("year") or ""
            try:
                year = int(year_raw)
            except Exception:
                continue
            slug = make_spine_slug(title, artist)
            mapping[(year, slug)] = SpineRow(spine_track_id=sid, year=year, title=title, artist=artist)
    return mapping


def parse_float(val: str) -> str:
    try:
        return str(float(val))
    except Exception:
        return ""


def parse_int(val: str) -> int:
    try:
        return int(float(val))
    except Exception:
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Map tonyrwen features to Tier 2 spine by slug/year.")
    parser.add_argument(
        "--spine-core",
        default=str(get_spine_root() / "spine_core_tracks_tier2_modern_v1.csv"),
        help="Tier 2 core spine CSV (with spine_track_id).",
    )
    parser.add_argument(
        "--tonyrwen-csv",
        default=str(get_external_data_root() / "year_end/year_end_top_100_features_tonyrwen_1970_2020/primary_dataset.csv"),
        help="tonyrwen Year-End Top 100 features CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(get_spine_root() / "backfill" / "spine_audio_from_tonyrwen_tier2_modern_v1.csv"),
        help="Output path for mapped audio rows.",
    )
    parser.add_argument("--year-min", type=int, default=1985, help="Minimum year to include.")
    parser.add_argument("--year-max", type=int, default=2024, help="Maximum year to include.")
    args = parser.parse_args()

    spine_path = Path(args.spine_core)
    tonyrwen_path = Path(args.tonyrwen_csv)
    out_path = Path(args.out)

    print(f"[INFO] Loading Tier 2 spine core from {spine_path} ...")
    spine_map = load_spine_core(spine_path)
    print(f"[INFO] Spine map entries: {len(spine_map)}")

    if not tonyrwen_path.exists():
        raise SystemExit(f"[ERROR] tonyrwen CSV not found: {tonyrwen_path}")

    fieldnames = [
        "spine_track_id",
        "year",
        "title",
        "artist",
        "spotify_id",
        "audio_source",
        "danceability",
        "energy",
        "key",
        "loudness",
        "mode",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
        "duration_ms",
        "time_signature",
    ]

    total = matched = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Mapping tonyrwen features from {tonyrwen_path} ...")
    with tonyrwen_path.open("r", encoding="utf-8", errors="replace", newline="") as f_in, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            total += 1
            year_raw = row.get("year") or row.get("Year") or ""
            try:
                year = int(year_raw)
            except Exception:
                continue
            if year < args.year_min or year > args.year_max:
                continue

            rank_raw = row.get("No.") or row.get("rank") or row.get("yearend_rank") or ""
            try:
                rank = int(rank_raw)
            except Exception:
                rank = None
            if rank is None or not (1 <= rank <= 100):
                continue

            title = (row.get("Title") or row.get("title") or "").strip()
            artist = (row.get("Artist(s)") or row.get("artist") or "").strip()
            if not title or not artist:
                continue
            slug = make_spine_slug(title, artist)
            spine_row = spine_map.get((year, slug))
            if spine_row is None:
                continue

            spotify_id = (row.get("id") or row.get("spotify_id") or "").strip()
            duration_ms = parse_int(row.get("duration_ms") or row.get("duration") or "0")

            writer.writerow(
                {
                    "spine_track_id": spine_row.spine_track_id,
                    "year": year,
                    "title": title,
                    "artist": artist,
                    "spotify_id": spotify_id,
                    "audio_source": "tonyrwen_v1",
                    "danceability": parse_float(row.get("danceability", "")),
                    "energy": parse_float(row.get("energy", "")),
                    "key": parse_int(row.get("key", "0")),
                    "loudness": parse_float(row.get("loudness", "")),
                    "mode": parse_int(row.get("mode", "0")),
                    "speechiness": parse_float(row.get("speechiness", "")),
                    "acousticness": parse_float(row.get("acousticness", "")),
                    "instrumentalness": parse_float(row.get("instrumentalness", "")),
                    "liveness": parse_float(row.get("liveness", "")),
                    "valence": parse_float(row.get("valence", "")),
                    "tempo": parse_float(row.get("tempo", "")),
                    "duration_ms": duration_ms,
                    "time_signature": parse_int(row.get("time_signature", "0")),
                }
            )
            matched += 1

    print("[INFO] Mapping complete.")
    print(f"  Total tonyrwen rows scanned : {total}")
    print(f"  Matched to Tier 2 spine     : {matched}")
    print(f"  Unmatched or out-of-range   : {total - matched}")
    print(f"[INFO] Wrote mapped audio to {out_path}")


if __name__ == "__main__":
    main()
