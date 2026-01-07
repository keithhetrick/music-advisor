#!/usr/bin/env python3
"""
backfill_tier1_from_rodolfo.py

Map rodolfo 1.2M Spotify tracks onto Tier 1 (spine_master_v1_lanes) by (year, slug)
to fill missing audio. Only updates rows where has_audio != 1. Tier 2/3 untouched.
"""
from __future__ import annotations

import argparse
import ast
import csv
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from shared.security import db as sec_db
from adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_historical_echo_db_path, get_external_data_root

ensure_repo_root()

from tools.spine.spine_slug import make_spine_slug


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


def load_rodolfo(path: Path, year_min: int, year_max: int) -> Dict[Tuple[int, str], Dict[str, str]]:
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
                "audio_source": "rodolfo_1_2m",
            }
    return out


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill Tier 1 audio from rodolfo 1.2M Spotify set.")
    default_db = get_historical_echo_db_path()
    p.add_argument("--db", default=str(default_db), help=f"SQLite DB path (default: {default_db}).")
    p.add_argument("--table", default="spine_master_v1_lanes", help="Tier 1 table name.")
    p.add_argument("--echo-tier", default="EchoTier_1_YearEnd_Top40", help="Tier 1 echo label.")
    default_rodolfo = get_external_data_root() / "weekly" / "spotify_1.2_million_songs_rodolfo_figueroa.csv"
    p.add_argument("--rodolfo-csv", default=str(default_rodolfo), help="Rodolfo 1.2M CSV path.")
    p.add_argument("--year-min", type=int, default=1985, help="Minimum year to match.")
    p.add_argument("--year-max", type=int, default=2024, help="Maximum year to match.")
    p.add_argument("--dry-run", action="store_true", help="Show matches without updating DB.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser()
    rodolfo_path = Path(args.rodolfo_csv).expanduser()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    source_map = load_rodolfo(rodolfo_path, args.year_min, args.year_max)
    print(f"[INFO] Loaded rodolfo entries: {len(source_map)}")

    # Some Tier 1 tables may not have a slug column; compute on the fly if missing.
    sec_db.validate_table_name(args.table)
    cols = {row[1]: True for row in sec_db.safe_execute(conn, f"PRAGMA table_info({args.table})")}
    has_slug_col = cols.get("slug", False)
    select_slug = "slug" if has_slug_col else "title || ' ' || artist"

    targets = sec_db.safe_execute(
        conn,
        f"""
        SELECT id, year, title, artist, {select_slug} AS slug, has_audio
        FROM {args.table}
        WHERE echo_tier = ? AND (has_audio = '0' OR has_audio = '' OR has_audio IS NULL)
        """,
        (args.echo_tier,),
    ).fetchall()
    print(f"[INFO] Tier 1 rows needing audio: {len(targets)}")

    updated = 0
    for r in targets:
        try:
            year = int(r["year"])
        except Exception:
            continue
        slug = r["slug"] or make_spine_slug(r["title"], r["artist"])
        match = source_map.get((year, slug))
        if not match:
            continue

        tempo = safe_float(match.get("tempo"))
        valence = safe_float(match.get("valence"))
        loudness = safe_float(match.get("loudness"))
        if tempo is None or valence is None or loudness is None:
            continue

        energy = safe_float(match.get("energy"))
        duration_ms = match.get("duration_ms", "")

        payload = {
            "tempo": str(tempo),
            "valence": str(valence),
            "loudness": str(loudness),
            "energy": str(energy) if energy is not None else "",
            "duration_ms": duration_ms,
            "acousticness": match.get("acousticness", ""),
            "danceability": match.get("danceability", ""),
            "instrumentalness": match.get("instrumentalness", ""),
            "liveness": match.get("liveness", ""),
            "speechiness": match.get("speechiness", ""),
            "key": match.get("key", ""),
            "mode": match.get("mode", ""),
            "time_signature": match.get("time_signature", ""),
            "audio_source": match.get("audio_source", "rodolfo_1_2m"),
            "has_audio": "1",
            "tempo_band": band_tempo(tempo),
            "valence_band": band_valence(valence),
            "energy_band": band_energy(energy),
            "loudness_band": band_loudness(loudness),
        }

        if args.dry_run:
            print(f"[DRY] would update Tier1 id={r['id']} ({year} {r['artist']} — {r['title']})")
            continue

        conn.execute(
            f"""
            UPDATE {args.table}
            SET tempo = :tempo,
                valence = :valence,
                loudness = :loudness,
                energy = :energy,
                duration_ms = :duration_ms,
                acousticness = :acousticness,
                danceability = :danceability,
                instrumentalness = :instrumentalness,
                liveness = :liveness,
                speechiness = :speechiness,
                key = :key,
                mode = :mode,
                time_signature = :time_signature,
                audio_source = :audio_source,
                has_audio = :has_audio,
                tempo_band = :tempo_band,
                valence_band = :valence_band,
                energy_band = :energy_band,
                loudness_band = :loudness_band
            WHERE id = :id
            """,
            {**payload, "id": r["id"]},
        )
        updated += 1

    if not args.dry_run:
        conn.commit()
    print(f"[INFO] Updated Tier 1 rows: {updated}")


if __name__ == "__main__":
    main()
