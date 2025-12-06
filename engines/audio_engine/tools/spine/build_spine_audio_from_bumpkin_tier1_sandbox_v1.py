#!/usr/bin/env python3
"""
Sandbox mapping of Bumpkin dataset to Tier1 spine; env-driven paths.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from adapters.bootstrap import ensure_repo_root
from tools.audio.spine.common_paths import spine_root_override, spine_backfill_root_override
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Map Bumpkin dataset to Tier1 spine (sandbox).")
    parser.add_argument("--spine-core", help="Tier1 core spine CSV (with spine_track_id).")
    parser.add_argument("--bumpkin-csv", help="Bumpkin dataset CSV.")
    parser.add_argument("--spine-root", help="Spine root (env MA_SPINE_ROOT or <data>/spine).")
    parser.add_argument("--backfill-root", help="Backfill root (env MA_SPINE_BACKFILL_ROOT or <data>/spine/backfill).")
    parser.add_argument("--out", help="Output path (default under backfill root).")
    args = parser.parse_args()

    spine_root = spine_root_override(args.spine_root)
    backfill_root = spine_backfill_root_override(args.backfill_root)
    spine_path = Path(args.spine_core) if args.spine_core else spine_root / "spine_core_tracks_tier1_sandbox_v1.csv"
    bumpkin_default = spine_root.parent / "external" / "weekly" / "600 Billboard Hot 100 Tracks (with Spotify Data) - The Bumpkin.csv"
    bumpkin_path = Path(args.bumpkin_csv) if args.bumpkin_csv else bumpkin_default
    out_path = Path(args.out) if args.out else backfill_root / "spine_audio_from_bumpkin_tier1_sandbox_v1.csv"

    spine_map = load_spine_core(spine_path)
    if not bumpkin_path.exists():
        raise SystemExit(f"[ERROR] Bumpkin CSV not found: {bumpkin_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with bumpkin_path.open("r", encoding="utf-8", errors="replace", newline="") as f_in, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=["spine_track_id", "year", "title", "artist", "audio_source"])
        writer.writeheader()
        for row in reader:
            year = row.get("Year") or row.get("year")
            try:
                year_int = int(year) if year else None
            except Exception:
                continue
            title = (row.get("Track") or row.get("Song") or row.get("title") or "").strip()
            artist = (row.get("Artist") or row.get("artist") or "").strip()
            if not year_int or not title or not artist:
                continue
            slug = make_spine_slug(title, artist)
            spine_row = spine_map.get((year_int, slug))
            if not spine_row:
                continue
            writer.writerow(
                {
                    "spine_track_id": spine_row.spine_track_id,
                    "year": spine_row.year,
                    "title": spine_row.title,
                    "artist": spine_row.artist,
                    "audio_source": "bumpkin_v1",
                }
            )
    print(f"[DONE] Wrote Tier1 bumpkin backfill to {out_path}")


if __name__ == "__main__":
    main()
