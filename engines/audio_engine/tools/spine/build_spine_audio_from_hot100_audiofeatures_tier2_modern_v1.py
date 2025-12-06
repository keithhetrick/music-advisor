#!/usr/bin/env python3
"""
Map Hot100 audio features to Tier2 spine; env-driven paths.
"""
from __future__ import annotations

import argparse
import csv
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

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


def parse_weekid_to_year(weekid: str) -> Optional[int]:
    try:
        return datetime.datetime.strptime(weekid, "%m/%d/%Y").year
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Tier2 spine audio from Hot100 audio features.")
    spine_root = get_spine_root()
    external_root = get_external_data_root()
    parser.add_argument(
        "--spine-core",
        default=str(spine_root / "spine_core_tracks_tier2_modern_v1.csv"),
        help="Tier2 core spine CSV (with spine_track_id).",
    )
    parser.add_argument(
        "--hot100-audio",
        default=str(external_root / "weekly" / "Hot 100 Audio Features.csv"),
        help="Hot 100 Audio Features CSV.",
    )
    parser.add_argument(
        "--hot100-weeks",
        default=str(external_root / "weekly" / "Hot Stuff.csv"),
        help="Hot Stuff CSV (WeekID to SongID mapping).",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "backfill" / "spine_audio_from_hot100_audiofeatures_tier2_modern_v1.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    spine_core = load_spine_core(Path(args.spine_core).expanduser())
    audio_path = Path(args.hot100_audio).expanduser()
    weeks_path = Path(args.hot100_weeks).expanduser()
    out_path = Path(args.out).expanduser()

    if not audio_path.exists() or not weeks_path.exists():
        raise SystemExit("[ERROR] Hot 100 CSV inputs missing.")

    song_to_year: Dict[str, int] = {}
    with weeks_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songid = row.get("SongID") or ""
            weekid = row.get("WeekID") or ""
            if not songid or not weekid:
                continue
            year = parse_weekid_to_year(weekid)
            if year:
                song_to_year.setdefault(songid, year)

    features: Dict[Tuple[int, str], Dict[str, str]] = {}
    with audio_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songid = row.get("SongID") or ""
            title = row.get("Song") or ""
            artist = row.get("Artist") or ""
            if not songid or not title or not artist:
                continue
            year = song_to_year.get(songid)
            if year is None:
                continue
            slug = make_spine_slug(title, artist)
            features[(year, slug)] = {
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
                "audio_source": "hot100_audiofeatures_v1",
            }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f_out:
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
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        written = 0
        for (year, slug), feature_row in features.items():
            spine_row = spine_core.get((year, slug))
            if not spine_row:
                continue
            row = {
                "spine_track_id": spine_row.spine_track_id,
                "year": spine_row.year,
                "title": spine_row.title,
                "artist": spine_row.artist,
            }
            row.update(feature_row)
            writer.writerow(row)
            written += 1

    print(f"[DONE] Wrote {written} rows to {out_path}")


if __name__ == "__main__":
    main()
