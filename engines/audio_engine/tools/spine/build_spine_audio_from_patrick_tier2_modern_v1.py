#!/usr/bin/env python3
"""
Map Patrick Year-End Hot 100 Spotify features (1960–2020) onto Tier2 spine (env-driven paths).
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_spine_root, get_external_data_root
from tools.spine.spine_slug import make_spine_slug, make_year_slug_key

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
    parser = argparse.ArgumentParser(description="Backfill Tier2 spine audio from Patrick Spotify features.")
    spine_root = get_spine_root()
    ext_root = get_external_data_root()
    parser.add_argument(
        "--spine-core",
        default=str(spine_root / "spine_core_tracks_tier2_modern_v1.csv"),
        help="Tier2 core spine CSV (with spine_track_id).",
    )
    parser.add_argument(
        "--patrick-csv",
        default=str(ext_root / "year_end" / "year_end_hot_100_spotify_features_patrick_1960_2020.csv"),
        help="Patrick year-end Spotify features CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "backfill" / "spine_audio_from_patrick_tier2_modern_v1.csv"),
        help="Output backfill CSV path.",
    )
    args = parser.parse_args()

    spine_map = load_spine_core(Path(args.spine_core).expanduser())
    patrick_path = Path(args.patrick_csv).expanduser()
    out_path = Path(args.out).expanduser()

    if not patrick_path.exists():
        raise SystemExit(f"[ERROR] Patrick CSV not found: {patrick_path}")

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
    with patrick_path.open("r", encoding="utf-8", errors="replace", newline="") as f_in, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            try:
                year = int(row.get("Year") or row.get("year") or 0)
            except Exception:
                continue
            title = (row.get("Song") or row.get("song") or "").strip()
            artist = (row.get("Artist") or row.get("artist") or "").strip()
            if not title or not artist:
                continue
            slug = make_spine_slug(title, artist)
            spine_row = spine_map.get((year, slug))
            if not spine_row:
                continue

            writer.writerow(
                {
                    "spine_track_id": spine_row.spine_track_id,
                    "year": spine_row.year,
                    "title": spine_row.title,
                    "artist": spine_row.artist,
                    "audio_source": "patrick_hot100_audiofeatures_v1",
                    "tempo": row.get("Tempo") or row.get("tempo") or "",
                    "energy": row.get("Energy") or "",
                    "loudness": row.get("Loudness") or "",
                    "danceability": row.get("Danceability") or "",
                    "valence": row.get("Valence") or "",
                    "acousticness": row.get("Acousticness") or "",
                    "instrumentalness": row.get("Instrumentalness") or "",
                    "liveness": row.get("Liveness") or "",
                    "speechiness": row.get("Speechiness") or "",
                    "duration_ms": row.get("duration_ms") or row.get("Duration_ms") or "",
                    "key": row.get("Key") or "",
                    "mode": row.get("Mode") or "",
                    "time_signature": row.get("Time_Signature") or "",
                }
            )
            written += 1

    print(f"[DONE] Wrote {written} rows to {out_path}")


if __name__ == "__main__":
    main()
