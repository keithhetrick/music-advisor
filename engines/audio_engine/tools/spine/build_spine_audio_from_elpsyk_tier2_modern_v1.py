#!/usr/bin/env python3
"""
Map elpsyk Hot100 audio features to Tier2 spine (env-driven paths).
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_spine_root, get_external_data_root
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
    parser = argparse.ArgumentParser(description="Backfill Tier2 spine audio from elpsyk Hot100 audio features.")
    spine_root = get_spine_root()
    ext_root = get_external_data_root()
    parser.add_argument(
        "--spine-core",
        default=str(spine_root / "spine_core_tracks_tier2_modern_v1.csv"),
        help="Tier2 spine core CSV (with spine_track_id).",
    )
    parser.add_argument(
        "--elpsyk-csv",
        default=str(ext_root / "weekly" / "Spotify Audio Features for Billboard Hot 100 - elpsyk" / "billboard_top_100_final.csv"),
        help="Elpsyk Hot100 audio features CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "backfill" / "spine_audio_from_elpsyk_tier2_modern_v1.csv"),
        help="Output backfill CSV path.",
    )
    args = parser.parse_args()

    spine_path = Path(args.spine_core).expanduser()
    elpsyk_path = Path(args.elpsyk_csv).expanduser()
    out_path = Path(args.out).expanduser()

    spine_core = load_spine_core(spine_path)
    if not elpsyk_path.exists():
        raise SystemExit(f"[ERROR] Elpsyk CSV not found: {elpsyk_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "spine_track_id",
        "year",
        "title",
        "artist",
        "audio_source",
        "tempo",
        "energy",
        "loudness",
        "danceability",
        "valence",
        "acousticness",
        "instrumentalness",
        "liveness",
        "speechiness",
        "duration_ms",
        "key",
        "mode",
        "time_signature",
    ]

    written = 0
    with elpsyk_path.open("r", encoding="utf-8", errors="replace", newline="") as f_in, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            try:
                year = int(row.get("Year") or 0)
            except Exception:
                continue
            title = (row.get("Song") or "").strip()
            artist = (row.get("Artist") or "").strip()
            if not title or not artist:
                continue
            slug = make_spine_slug(title, artist)
            spine_row = spine_core.get((year, slug))
            if not spine_row:
                continue

            writer.writerow(
                {
                    "spine_track_id": spine_row.spine_track_id,
                    "year": spine_row.year,
                    "title": spine_row.title,
                    "artist": spine_row.artist,
                    "audio_source": "elpsyk_hot100_audiofeatures_v1",
                    "tempo": row.get("tempo") or row.get("Tempo") or "",
                    "energy": row.get("energy") or "",
                    "loudness": row.get("loudness") or "",
                    "danceability": row.get("danceability") or "",
                    "valence": row.get("valence") or "",
                    "acousticness": row.get("acousticness") or "",
                    "instrumentalness": row.get("instrumentalness") or "",
                    "liveness": row.get("liveness") or "",
                    "speechiness": row.get("speechiness") or "",
                    "duration_ms": row.get("duration_ms") or "",
                    "key": row.get("key") or "",
                    "mode": row.get("mode") or "",
                    "time_signature": row.get("time_signature") or "",
                }
            )
            written += 1

    print(f"[DONE] Wrote {written} rows to {out_path}")


if __name__ == "__main__":
    main()
