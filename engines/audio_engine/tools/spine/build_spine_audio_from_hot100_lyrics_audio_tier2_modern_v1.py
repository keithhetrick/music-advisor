#!/usr/bin/env python3
"""
Map hot_100_lyrics_audio_2000_2023 onto Tier2 spine (env-driven paths).
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


def normalize(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def load_spine_core(path: Path) -> Dict[Tuple[int, str], SpineRow]:
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
    parser = argparse.ArgumentParser(description="Backfill Tier2 spine audio from hot_100_lyrics_audio_2000_2023.")
    spine_root = get_spine_root()
    ext_root = get_external_data_root()
    parser.add_argument("--spine-core", default=str(spine_root / "spine_core_tracks_tier2_modern_v1.csv"))
    parser.add_argument(
        "--lyrics-audio",
        default=str(ext_root / "lyrics" / "hot_100_lyrics_audio_2000_2023.csv"),
        help="Lyrics+audio dataset CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "backfill" / "spine_audio_from_hot100_lyrics_audio_tier2_modern_v1.csv"),
        help="Output backfill CSV path.",
    )
    args = parser.parse_args()

    spine_map = load_spine_core(Path(args.spine_core).expanduser())
    la_path = Path(args.lyrics_audio).expanduser()
    out_path = Path(args.out).expanduser()

    if not la_path.exists():
        raise SystemExit(f"[ERROR] Lyrics+audio CSV not found: {la_path}")

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
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with la_path.open("r", encoding="utf-8", errors="replace", newline="") as f_in, out_path.open(
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
            title = (row.get("song") or row.get("Song") or row.get("titletext") or "").strip()
            artist = (row.get("band_singer") or row.get("artist") or row.get("Artist") or "").strip()
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
                    "audio_source": "hot100_lyrics_audio_v1",
                    "tempo": row.get("tempo") or "",
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
