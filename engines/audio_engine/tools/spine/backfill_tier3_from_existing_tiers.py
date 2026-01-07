#!/usr/bin/env python3
"""
backfill_tier3_from_existing_tiers.py

Reuse Tier 1 / Tier 2 audio (in SQLite) to fill Tier 3 rows that are missing audio.
Matching is by (year, slug) with preference: Tier 1 > Tier 2.

Updates (in-place) the Tier 3 table with:
  - audio columns: tempo, valence, energy, loudness, duration_ms, acousticness,
                   danceability, instrumentalness, liveness, speechiness,
                   key, mode, time_signature, audio_source (if present)
  - has_audio = 1
  - band columns recomputed

Tier 1 / Tier 2 tables are read-only here.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple
from shared.security import db as sec_db
from adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_historical_echo_db_path

# Allow running as script without editable install
ensure_repo_root()

from tools.spine.spine_slug import make_spine_slug

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


AudioFields = Dict[str, str]


def table_columns(conn: sqlite3.Connection, table: str) -> Dict[str, bool]:
    cols = {}
    sec_db.validate_table_name(table)
    for _, name, _, _, _, _ in sec_db.safe_execute(conn, f"PRAGMA table_info({table})"):
        cols[name] = True
    return cols


def load_source_map(conn: sqlite3.Connection, table: str, echo_tier: str) -> Dict[Tuple[int, str], AudioFields]:
    cols = table_columns(conn, table)
    select_cols = ["year", "title", "artist"]
    for c in [
        "slug",
        "tempo",
        "valence",
        "energy",
        "loudness",
        "duration_ms",
        "acousticness",
        "danceability",
        "instrumentalness",
        "liveness",
        "speechiness",
        "key",
        "mode",
        "time_signature",
        "audio_source",
    ]:
        if cols.get(c):
            select_cols.append(c)

    select_clause = ", ".join(select_cols)
    q = f"""
        SELECT {select_clause}
        FROM {table}
        WHERE echo_tier = ? AND has_audio = '1'
    """
    rows: Dict[Tuple[int, str], AudioFields] = {}
    for r in conn.execute(q, (echo_tier,)):
        try:
            year = int(r["year"])
        except Exception:
            continue
        title = r["title"]
        artist = r["artist"]
        slug = r["slug"] if "slug" in r.keys() else None
        slug = slug or make_spine_slug(title, artist)
        rows[(year, slug)] = {k: (r[k] if k in r.keys() and r[k] is not None else "") for k in select_cols if k not in ("year", "title", "artist", "slug")}
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill Tier 3 audio from Tier 1/2 tables by (year, slug).")
    default_db = get_historical_echo_db_path()
    p.add_argument("--db", default=str(default_db), help=f"Path to SQLite DB (default: {default_db}).")
    p.add_argument("--tier3-table", default="spine_master_tier3_modern_lanes_v1", help="Tier 3 table name.")
    p.add_argument("--tier1-table", default="spine_master_v1_lanes", help="Tier 1 table name.")
    p.add_argument("--tier2-table", default="spine_master_tier2_modern_lanes_v1", help="Tier 2 table name.")
    p.add_argument("--tier1-echo", default="EchoTier_1_YearEnd_Top40", help="Tier 1 echo label.")
    p.add_argument("--tier2-echo", default="EchoTier_2_YearEnd_Top100_Modern", help="Tier 2 echo label.")
    p.add_argument("--dry-run", action="store_true", help="Show matches without updating DB.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.is_file():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    tier1_map = load_source_map(conn, args.tier1_table, args.tier1_echo)
    tier2_map = load_source_map(conn, args.tier2_table, args.tier2_echo)
    print(f"[INFO] Loaded Tier1 audio rows: {len(tier1_map)}; Tier2 audio rows: {len(tier2_map)}")

    sec_db.validate_table_name(args.tier3_table)
    q_t3 = f"""
        SELECT id, year, slug, title, artist, has_audio, tempo, valence, loudness
        FROM {args.tier3_table}
    """
    rows = sec_db.safe_execute(conn, q_t3).fetchall()
    updated = 0
    matched_t1 = 0
    matched_t2 = 0

    for r in rows:
        try:
            year = int(r["year"])
        except Exception:
            continue
        slug = r["slug"]
        if not slug:
            continue

        has_audio = str(r["has_audio"] or "").strip()
        if has_audio in ("1", "true", "True"):
            continue  # already has audio

        source = tier1_map.get((year, slug))
        source_from = None
        if source:
            source_from = "tier1"
            matched_t1 += 1
        else:
            source = tier2_map.get((year, slug))
            if source:
                source_from = "tier2"
                matched_t2 += 1
        if not source:
            continue

        tempo = safe_float(source.get("tempo"))
        valence = safe_float(source.get("valence"))
        loudness = safe_float(source.get("loudness"))
        energy = safe_float(source.get("energy"))
        duration_ms = source.get("duration_ms") or ""

        if tempo is None or valence is None or loudness is None:
            continue

        lane_fields = {
            "tempo_band": band_tempo(tempo),
            "valence_band": band_valence(valence),
            "energy_band": band_energy(energy),
            "loudness_band": band_loudness(loudness),
        }

        # Build update payload
        payload = {
            "tempo": str(tempo),
            "valence": str(valence),
            "loudness": str(loudness),
            "energy": str(energy) if energy is not None else "",
            "duration_ms": str(int(duration_ms)) if str(duration_ms).isdigit() else str(duration_ms),
            "acousticness": source.get("acousticness", ""),
            "danceability": source.get("danceability", ""),
            "instrumentalness": source.get("instrumentalness", ""),
            "liveness": source.get("liveness", ""),
            "speechiness": source.get("speechiness", ""),
            "key": source.get("key", ""),
            "mode": source.get("mode", ""),
            "time_signature": source.get("time_signature", ""),
            "audio_source": source.get("audio_source", source_from or ""),
            "has_audio": "1",
            "tempo_band": lane_fields["tempo_band"],
            "valence_band": lane_fields["valence_band"],
            "energy_band": lane_fields["energy_band"],
            "loudness_band": lane_fields["loudness_band"],
        }

        if args.dry_run:
            print(f"[DRY] would update {r['id']} ({year} {r['artist']} — {r['title']}) from {source_from}")
            continue

        conn.execute(
            f"""
            UPDATE {args.tier3_table}
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

    print(
        f"[INFO] Done. matched_tier1={matched_t1}, matched_tier2={matched_t2}, "
        f"updated={updated} (has_audio set to 1)."
    )


if __name__ == "__main__":
    main()
