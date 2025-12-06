#!/usr/bin/env python3
"""
Map yamaerenay 600k Spotify dump onto Tier2 spine; env-driven paths.
"""
from __future__ import annotations

import argparse
import ast
import csv
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


def parse_first_artist(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list) and parsed:
                return str(parsed[0])
        except Exception:
            pass
    for sep in [";", ",", "/", "|", " feat ", " featuring "]:
        if sep in raw:
            return raw.split(sep)[0]
    return raw


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


def load_yamaerenay(path: Path, year_min: int, year_max: int) -> Dict[Tuple[int, str], Dict[str, str]]:
    out: Dict[Tuple[int, str], Dict[str, str]] = {}
    if not path.is_file():
        return out
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("name") or "").strip()
            artist = parse_first_artist(row.get("artists") or "")
            if not title or not artist:
                continue
            rd = (row.get("release_date") or "").strip()
            if len(rd) < 4 or not rd[:4].isdigit():
                continue
            year = int(rd[:4])
            if year < year_min or year > year_max:
                continue
            slug = make_spine_slug(title, artist)
            out[(year, slug)] = {
                "tempo": row.get("tempo", ""),
                "valence": row.get("valence", ""),
                "energy": row.get("energy", ""),
                "loudness": row.get("loudness", ""),
                "danceability": row.get("danceability", ""),
                "acousticness": row.get("acousticness", ""),
                "instrumentalness": row.get("instrumentalness", ""),
                "liveness": row.get("liveness", ""),
                "speechiness": row.get("speechiness", ""),
                "duration_ms": row.get("duration_ms", ""),
                "key": row.get("key", ""),
                "mode": row.get("mode", ""),
                "time_signature": row.get("time_signature", ""),
                "audio_source": "yamaerenay_600k",
            }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Tier2 spine audio from yamaerenay 600k Spotify dump.")
    spine_root = get_spine_root()
    ext_root = get_external_data_root()
    parser.add_argument("--spine-core", default=str(spine_root / "spine_core_tracks_tier2_modern_v1.csv"))
    parser.add_argument(
        "--yama-csv",
        default=str(ext_root / "weekly" / "spotify_dataset_19212020_600k_tracks_yamaerenay" / "tracks.csv"),
        help="yamaerenay 600k tracks CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(spine_root / "backfill" / "spine_audio_from_yamaerenay_tier2_modern_v1.csv"),
        help="Output backfill CSV path.",
    )
    parser.add_argument("--year-min", type=int, default=1985)
    parser.add_argument("--year-max", type=int, default=2024)
    args = parser.parse_args()

    spine_core = load_spine_core(Path(args.spine_core).expanduser())
    yama_path = Path(args.yama_csv).expanduser()
    out_path = Path(args.out).expanduser()

    audio_map = load_yamaerenay(yama_path, args.year_min, args.year_max)

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
    with out_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for (year, slug), feat in audio_map.items():
            spine_row = spine_core.get((year, slug))
            if not spine_row:
                continue
            row = {
                "spine_track_id": spine_row.spine_track_id,
                "year": spine_row.year,
                "title": spine_row.title,
                "artist": spine_row.artist,
            }
            row.update(feat)
            writer.writerow(row)
            written += 1

    print(f"[DONE] Wrote {written} rows to {out_path}")


if __name__ == "__main__":
    main()
