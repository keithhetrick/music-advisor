#!/usr/bin/env python3
"""
Map the Bumpkin 600-track CSV onto Tier2 spine and emit a backfill CSV.

Defaults are env-driven via ma_config:
- Spine root: MA_SPINE_ROOT or <data>/spine
- Backfill root: MA_SPINE_BACKFILL_ROOT or <data>/spine/backfill
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from adapters.bootstrap import ensure_repo_root
from tools.audio.spine.common_paths import (
    spine_root_override,
    spine_backfill_root_override,
)
from tools.spine.spine_slug import make_spine_slug

ensure_repo_root()


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
    parser = argparse.ArgumentParser(description="Map Bumpkin 600 Hot 100 tracks to Tier2 spine backfill.")
    parser.add_argument("--spine-core", help="Tier2 core spine CSV (with spine_track_id). Defaults to <spine_root>/spine_core_tracks_tier2_modern_v1.csv.")
    parser.add_argument("--bumpkin-csv", help="Bumpkin dataset CSV (defaults under external data).")
    parser.add_argument("--spine-root", help="Spine root (env MA_SPINE_ROOT or <data>/spine).")
    parser.add_argument("--backfill-root", help="Backfill root (env MA_SPINE_BACKFILL_ROOT or <data>/spine/backfill).")
    parser.add_argument("--out", help="Output path for mapped audio rows (default under backfill root).")
    parser.add_argument("--year-min", type=int, default=1985, help="Minimum year to include.")
    parser.add_argument("--year-max", type=int, default=2024, help="Maximum year to include.")
    args = parser.parse_args()

    spine_root = spine_root_override(args.spine_root)
    backfill_root = spine_backfill_root_override(args.backfill_root)
    spine_path = Path(args.spine_core) if args.spine_core else spine_root / "spine_core_tracks_tier2_modern_v1.csv"
    bumpkin_default = spine_root.parent / "external" / "weekly" / "600 Billboard Hot 100 Tracks (with Spotify Data) - The Bumpkin.csv"
    bumpkin_path = Path(args.bumpkin_csv) if args.bumpkin_csv else bumpkin_default
    out_path = Path(args.out) if args.out else backfill_root / "spine_audio_from_bumpkin_tier2_modern_v1.csv"

    spine_map = load_spine_core(spine_path)
    if not bumpkin_path.exists():
        raise SystemExit(f"[ERROR] Bumpkin CSV not found: {bumpkin_path}")

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

    with bumpkin_path.open("r", encoding="utf-8", errors="replace", newline="") as f_in, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total += 1
            try:
                year = int(row.get("Year") or row.get("year") or 0)
            except Exception:
                continue
            if year < args.year_min or year > args.year_max:
                continue

            title = (row.get("Track") or row.get("Song") or row.get("title") or "").strip()
            artist = (row.get("Artist") or row.get("artist") or "").strip()
            if not title or not artist:
                continue
            slug = make_spine_slug(title, artist)
            spine_row = spine_map.get((year, slug))
            if spine_row is None:
                continue

            writer.writerow(
                {
                    "spine_track_id": spine_row.spine_track_id,
                    "year": year,
                    "title": spine_row.title,
                    "artist": spine_row.artist,
                    "spotify_id": "",  # not provided
                    "audio_source": "bumpkin_v1",
                    "danceability": parse_float(row.get("Danceability", "")),
                    "energy": parse_float(row.get("Energy", "")),
                    "key": parse_int(row.get("Key", "0")),
                    "loudness": parse_float(row.get("Loudness", "")),
                    "mode": parse_int(row.get("Mode", "")),
                    "speechiness": parse_float(row.get("Speechiness", "")),
                    "acousticness": parse_float(row.get("Acousticness", "")),
                    "instrumentalness": parse_float(row.get("Instrumentalness", "")),
                    "liveness": parse_float(row.get("Liveness", "")),
                    "valence": parse_float(row.get("Valence", "")),
                    "tempo": parse_float(row.get("Tempo", "")),
                    "duration_ms": parse_int(row.get("Duration_ms", "0")),
                    "time_signature": parse_int(row.get("Time_Signature", "4")),
                }
            )
            matched += 1

    print(f"[DONE] Mapped {matched}/{total} rows -> {out_path}")


if __name__ == "__main__":
    main()
