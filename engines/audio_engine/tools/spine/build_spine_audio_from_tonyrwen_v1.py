#!/usr/bin/env python3
"""
Backfill Tier1 spine audio from tonyrwen Year-End Top 100 Spotify features (primary_dataset.csv).
Env-driven paths via ma_config.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from ma_config.paths import get_spine_root, get_external_data_root
from tools.spine.spine_slug import make_spine_slug


@dataclass
class SpineRow:
    spine_track_id: str
    year: int
    title: str
    artist: str


def load_spine_master(path: Path) -> Dict[Tuple[int, str], SpineRow]:
    if not path.exists():
        raise SystemExit(f"[ERROR] Spine master not found: {path}")
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
    parser = argparse.ArgumentParser(description="Backfill Tier1 spine audio from tonyrwen Spotify features.")
    spine_root = get_spine_root()
    ext_root = get_external_data_root()
    parser.add_argument("--spine-master", default=str(spine_root / "spine_master_v1_lanes.csv"))
    parser.add_argument(
        "--tonyrwen-csv",
        default=str(ext_root / "year_end" / "year_end_top_100_features_tonyrwen_1970_2020" / "primary_dataset.csv"),
        help="tonyrwen primary_dataset.csv",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "backfill" / "spine_audio_from_tonyrwen_v1.csv"),
        help="Output backfill CSV.",
    )
    args = parser.parse_args()

    spine_master = load_spine_master(Path(args.spine_master).expanduser())
    src_path = Path(args.tonyrwen_csv).expanduser()
    out_path = Path(args.out).expanduser()

    if not src_path.exists():
        raise SystemExit(f"[ERROR] tonyrwen dataset not found: {src_path}")

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
    with src_path.open("r", encoding="utf-8", errors="replace", newline="") as f_in, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            try:
                year = int(row.get("year") or row.get("Year") or 0)
            except Exception:
                continue
            title = (row.get("title") or row.get("Title") or "").strip()
            artist = (row.get("artist") or row.get("Artist") or "").strip()
            if not title or not artist:
                continue
            slug = make_spine_slug(title, artist)
            spine_row = spine_master.get((year, slug))
            if not spine_row:
                continue
            writer.writerow(
                {
                    "spine_track_id": spine_row.spine_track_id,
                    "year": spine_row.year,
                    "title": spine_row.title,
                    "artist": spine_row.artist,
                    "audio_source": "tonyrwen_yearend_audio_v1",
                    "tempo": row.get("tempo") or row.get("Tempo") or "",
                    "energy": row.get("energy") or row.get("Energy") or "",
                    "loudness": row.get("loudness") or row.get("Loudness") or "",
                    "danceability": row.get("danceability") or row.get("Danceability") or "",
                    "valence": row.get("valence") or row.get("Valence") or "",
                    "acousticness": row.get("acousticness") or row.get("Acousticness") or "",
                    "instrumentalness": row.get("instrumentalness") or row.get("Instrumentalness") or "",
                    "liveness": row.get("liveness") or row.get("Liveness") or "",
                    "speechiness": row.get("speechiness") or row.get("Speechiness") or "",
                    "duration_ms": row.get("duration_ms") or row.get("Duration_ms") or "",
                    "key": row.get("key") or row.get("Key") or "",
                    "mode": row.get("mode") or row.get("Mode") or "",
                    "time_signature": row.get("time_signature") or row.get("Time_Signature") or "",
                }
            )
            written += 1

    print(f"[DONE] Wrote {written} rows to {out_path}")


if __name__ == "__main__":
    main()
