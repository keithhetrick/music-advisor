"""
Export helpers for lyric intelligence (bridge payloads, coverage reports).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import os
from typing import Dict, Optional

from ma_lyric_engine.utils import normalize_text
from ma_lyric_engine.lci_overlay import load_norms, find_lane, overlay_lci

_NORMS_CACHE = None
_NORMS_PATH_CACHE: Optional[Path] = None


def _get_norms(norms_path: Optional[Path]) -> Optional[Dict[str, object]]:
    global _NORMS_CACHE, _NORMS_PATH_CACHE
    path = norms_path
    if path is None:
        env_path = os.getenv("LYRIC_LCI_NORMS_PATH")
        if env_path:
            path = Path(env_path).expanduser()
    if not path:
        return None
    if _NORMS_CACHE is not None and _NORMS_PATH_CACHE == path:
        return _NORMS_CACHE
    if path.exists():
        _NORMS_CACHE = load_norms(path)
        _NORMS_PATH_CACHE = path
        return _NORMS_CACHE
    return None


def export_bridge_payload(
    conn: sqlite3.Connection,
    song_id: Optional[str],
    limit: int,
    norms_path: Optional[Path] = None,
) -> Dict[str, object]:
    # Pull optional LCI rows.
    lci_map = {}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT song_id, axis_structure, axis_prosody, axis_rhyme, axis_lexical, axis_pov, axis_theme,
               LCI_lyric_v1_raw, LCI_lyric_v1_final_score, profile
        FROM features_song_lci
        """
    )
    for row in cur.fetchall():
        lci_map[row[0]] = {
            "axes": {
                "structure_fit": row[1],
                "prosody_ttc_fit": row[2],
                "rhyme_texture_fit": row[3],
                "diction_style_fit": row[4],
                "pov_fit": row[5],
                "theme_fit": row[6],
            },
            "raw": row[7],
            "score": row[8],
            "calibration_profile": row[9],
        }

    # Pull optional TTC rows.
    ttc_map = {}
    cur.execute(
        """
        SELECT song_id, ttc_seconds_first_chorus, ttc_bar_position_first_chorus, estimation_method, profile, ttc_confidence
        FROM features_ttc
        """
    )
    for row in cur.fetchall():
        ttc_map[row[0]] = {
            "ttc_seconds_first_chorus": row[1],
            "ttc_bar_position_first_chorus": row[2],
            "estimation_method": row[3],
            "profile": row[4],
            "ttc_confidence": row[5],
        }

    cur = conn.cursor()
    if song_id:
        cur.execute(
            """
            SELECT s.song_id, s.title, s.artist, s.year, s.tier, s.era_bucket, fs.*, v.vector
            FROM features_song fs
            JOIN songs s ON s.song_id = fs.song_id
            JOIN features_song_vector v ON v.song_id = fs.song_id
            WHERE fs.song_id=?
            """,
            (song_id,),
        )
    else:
        cur.execute(
            """
            SELECT s.song_id, s.title, s.artist, s.year, s.tier, s.era_bucket, fs.*, v.vector
            FROM features_song fs
            JOIN songs s ON s.song_id = fs.song_id
            JOIN features_song_vector v ON v.song_id = fs.song_id
            LIMIT ?
            """,
            (limit,),
        )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    records = []
    for row in rows:
        rec = dict(zip(cols, row))
        vector = json.loads(rec.pop("vector"))
        song_id_val = rec.pop("song_id")
        rec_filtered = {
            "song_id": song_id_val,
            "title": rec.pop("title"),
            "artist": rec.pop("artist"),
            "year": rec.pop("year"),
            "tier": rec.pop("tier") if "tier" in rec else None,
            "era_bucket": rec.pop("era_bucket") if "era_bucket" in rec else None,
            "lyric_intel": {
                "structure_profile": {
                    "verse_count": rec.pop("verse_count"),
                    "pre_count": rec.pop("pre_count"),
                    "chorus_count": rec.pop("chorus_count"),
                    "bridge_count": rec.pop("bridge_count"),
                    "outro_count": rec.pop("outro_count"),
                    "section_pattern": rec.pop("section_pattern"),
                    "hook_density": rec.pop("hook_density"),
                    "repetition_rate": rec.pop("repetition_rate"),
                },
                "style_profile": {
                    "lexical_diversity": rec.pop("lexical_diversity"),
                    "avg_words_per_line": rec.pop("avg_words_per_line"),
                    "avg_syllables_per_line": rec.pop("avg_syllables_per_line"),
                    "explicit_fraction": rec.pop("explicit_fraction"),
                    "pov_first": rec.pop("pov_first"),
                    "pov_second": rec.pop("pov_second"),
                    "pov_third": rec.pop("pov_third"),
                },
                "sentiment_profile": {
                    "sentiment_mean": rec.pop("sentiment_mean"),
                    "sentiment_std": rec.pop("sentiment_std"),
                },
                "rhyme_profile": {
                    "rhyme_density": rec.pop("rhyme_density"),
                    "internal_rhyme_density": rec.pop("internal_rhyme_density"),
                },
                "theme_profile": {
                    "concreteness": rec.pop("concreteness"),
                    "love": rec.pop("theme_love"),
                    "heartbreak": rec.pop("theme_heartbreak"),
                    "empowerment": rec.pop("theme_empowerment"),
                    "nostalgia": rec.pop("theme_nostalgia"),
                    "flex": rec.pop("theme_flex"),
                    "spiritual": rec.pop("theme_spiritual"),
                    "family": rec.pop("theme_family"),
                    "small_town": rec.pop("theme_small_town"),
                },
                "prosody_profile": {
                    "syllable_density": rec.pop("syllable_density"),
                    "tempo_bpm": rec.pop("tempo_bpm"),
                    "duration_sec": rec.pop("duration_sec"),
                },
                "vector": vector,
            },
        }
        lci = lci_map.get(song_id_val)
        ttc = ttc_map.get(song_id_val)
        if lci:
            lane = {
                "profile": lci.get("calibration_profile"),
                "tier": rec_filtered.get("tier"),
                "era_bucket": rec_filtered.get("era_bucket"),
            }
            lci["lane"] = lane
            norms = _get_norms(norms_path)
            if norms and lane["tier"] is not None and lane["era_bucket"] is not None:
                lane_norm = find_lane(norms, lane["tier"], lane["era_bucket"], lane["profile"])
                if lane_norm:
                    overlay = overlay_lci(
                        song_axes=lci["axes"],
                        lci_score=lci["score"],
                        ttc_seconds=ttc.get("ttc_seconds_first_chorus") if ttc else None,
                        lane_norms=lane_norm,
                    )
                    lci["overlay"] = overlay
            rec_filtered["lyric_confidence_index"] = lci
        if ttc:
            rec_filtered["ttc_profile"] = ttc
        records.append(rec_filtered)
    return {"count": len(records), "items": records}


def coverage_report(conn: sqlite3.Connection, core_csv: Optional[Path], log) -> None:
    if not core_csv or not core_csv.exists():
        return
    cur = conn.cursor()
    cur.execute("SELECT song_id, title, artist, year FROM songs")
    have = {(row[1], row[2], row[3]): row[0] for row in cur.fetchall()}
    total = 0
    missing = 0
    with core_csv.open("r", encoding="utf-8", errors="replace") as f:
        import csv

        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            title = row.get("title") or row.get("Song") or ""
            artist = row.get("artist") or row.get("Artist") or ""
            try:
                year = int(row.get("year") or row.get("Year") or 0)
            except Exception:
                year = None
            key = (title, artist, year)
            found = None
            for candidate in (key, (normalize_text(title), normalize_text(artist), year)):
                for existing_key in have:
                    if (
                        normalize_text(existing_key[0]) == normalize_text(candidate[0])
                        and normalize_text(existing_key[1]) == normalize_text(candidate[1])
                        and existing_key[2] == candidate[2]
                    ):
                        found = existing_key
                        break
                if found:
                    break
            if not found:
                missing += 1
    log(f"[INFO] Coverage report: total={total}, present={total - missing}, missing={missing}")

__all__ = [
    "coverage_report",
    "export_bridge_payload",
]
