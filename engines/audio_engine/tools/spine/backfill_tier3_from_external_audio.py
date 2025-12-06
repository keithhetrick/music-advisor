#!/usr/bin/env python3
"""
Backfill Tier3 audio from external datasets; env-driven paths.
"""
from __future__ import annotations

import argparse
import ast
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_historical_echo_db_path, get_external_data_root
from tools.spine.spine_slug import make_spine_slug

ensure_repo_root()

YearSlug = Tuple[int, str]
AudioRow = Dict[str, str]


def safe_float(val: str | None) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def band_loudness(loudness: Optional[float]) -> str:
    if loudness is None:
        return ""
    if loudness < -18:
        return "loudness_very_quiet"
    if loudness < -14:
        return "loudness_quiet"
    if loudness < -10:
        return "loudness_mid"
    if loudness < -6:
        return "loudness_loud"
    return "loudness_very_loud"


def band_energy(energy: Optional[float]) -> str:
    if energy is None:
        return ""
    if energy < 0.2:
        return "energy_very_low"
    if energy < 0.4:
        return "energy_low"
    if energy < 0.6:
        return "energy_mid"
    if energy < 0.8:
        return "energy_high"
    return "energy_very_high"


def band_valence(valence: Optional[float]) -> str:
    if valence is None:
        return ""
    if valence < 0.2:
        return "valence_very_low"
    if valence < 0.4:
        return "valence_low"
    if valence < 0.6:
        return "valence_mid"
    if valence < 0.8:
        return "valence_high"
    return "valence_very_high"


def band_tempo(tempo: Optional[float]) -> str:
    if tempo is None:
        return ""
    if tempo < 80:
        return "tempo_sub_80"
    if tempo < 100:
        return "tempo_80_100"
    if tempo < 120:
        return "tempo_100_120"
    if tempo < 140:
        return "tempo_120_140"
    return "tempo_over_140"


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


def parse_audio_source(rows: Iterable[dict], title_field: str, artist_field: str, year_field: str) -> Dict[YearSlug, AudioRow]:
    out: Dict[YearSlug, AudioRow] = {}
    for r in rows:
        title = (r.get(title_field) or "").strip()
        artist = (r.get(artist_field) or "").strip()
        if not title or not artist:
            continue
        year_raw = (r.get(year_field) or "").strip()
        if not year_raw.isdigit():
            continue
        year = int(year_raw)
        slug = make_spine_slug(title, artist)
        out[(year, slug)] = {
            "tempo": r.get("tempo") or r.get("Tempo") or "",
            "valence": r.get("valence") or r.get("Valence") or "",
            "energy": r.get("energy") or r.get("Energy") or "",
            "loudness": r.get("loudness") or r.get("Loudness") or "",
            "danceability": r.get("danceability") or r.get("Danceability") or "",
            "acousticness": r.get("acousticness") or r.get("Acousticness") or "",
            "instrumentalness": r.get("instrumentalness") or r.get("Instrumentalness") or "",
            "liveness": r.get("liveness") or r.get("Liveness") or "",
            "speechiness": r.get("speechiness") or r.get("Speechiness") or "",
            "duration_ms": r.get("duration_ms") or r.get("Duration_ms") or "",
            "key": r.get("key") or r.get("Key") or "",
            "mode": r.get("mode") or r.get("Mode") or "",
            "time_signature": r.get("time_signature") or r.get("Time_Signature") or "",
            "audio_source": r.get("audio_source") or "",
        }
    return out


def load_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill Tier3 audio from external datasets (year, slug matching).")
    default_db = get_historical_echo_db_path()
    ap.add_argument("--db", default=str(default_db), help=f"Historical Echo DB path (default: {default_db}).")
    args = ap.parse_args()

    db_path = Path(args.db).expanduser()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    ext_root = get_external_data_root()
    sources = [
        ext_root / "spotify_dataset_19212020_600k_tracks_yamaerenay" / "tracks.csv",
        ext_root / "lyrics" / "hot_100_lyrics_audio_2000_2023.csv",
        ext_root / "year_end" / "year_end_hot_100_spotify_features_patrick_1960_2020.csv",
        ext_root / "year_end" / "year_end_top_100_features_tonyrwen_1970_2020" / "primary_dataset.csv",
        ext_root / "weekly" / "Spotify Audio Features for Billboard Hot 100 - elpsyk" / "billboard_top_100_final.csv",
        ext_root / "weekly" / "600 Billboard Hot 100 Tracks (with Spotify Data) - The Bumpkin.csv",
        ext_root / "weekly" / "spotify_1.2_million_songs_rodolfo_figueroa.csv",
    ]

    merged: Dict[YearSlug, AudioRow] = {}
    for src in sources:
        rows = load_csv(src)
        if not rows:
            continue
        parsed = parse_audio_source(rows, title_field="title" if "title" in rows[0] else "Track", artist_field="artist" if "artist" in rows[0] else "Artist", year_field="year" if "year" in rows[0] else "Year")
        merged.update(parsed)

    targets = conn.execute(
        """
        SELECT id, year, slug, title, artist, has_audio
        FROM spine_master_tier3_modern_lanes_v1
        WHERE has_audio IS NULL OR has_audio = '' OR has_audio = '0'
        """
    ).fetchall()

    updated = 0
    for row in targets:
        year = row["year"]
        slug = row["slug"] or make_spine_slug(row["title"], row["artist"])
        audio = merged.get((year, slug))
        if not audio:
            continue
        tempo = safe_float(audio.get("tempo"))
        valence = safe_float(audio.get("valence"))
        energy = safe_float(audio.get("energy"))
        loudness = safe_float(audio.get("loudness"))
        conn.execute(
            """
            UPDATE spine_master_tier3_modern_lanes_v1
            SET tempo=?, valence=?, energy=?, loudness=?, has_audio=1,
                band_tempo=?, band_valence=?, band_energy=?, band_loudness=?,
                audio_source=COALESCE(?, audio_source)
            WHERE id=?
            """,
            (
                tempo,
                valence,
                energy,
                loudness,
                band_tempo(tempo),
                band_valence(valence),
                band_energy(energy),
                band_loudness(loudness),
                audio.get("audio_source", "external"),
                row["id"],
            ),
        )
        updated += 1
    conn.commit()
    print(f"[DONE] Updated {updated} Tier3 rows with external audio.")


if __name__ == "__main__":
    main()
