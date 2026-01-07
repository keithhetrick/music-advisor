"""
Ingest helpers for lyric intelligence (upsert + corpus imports).
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Optional

from ma_lyric_engine.utils import clean_lyrics_text, normalize_text, slugify_song
from ma_lyric_engine.lanes import assign_lane

SOURCE_PRIORITY = {
    "ut_austin_billboard": 0,
    "kaggle_year_end": 1,
    "hot100_lyrics_audio": 2,
    "top100_fallback": 3,
}


def should_replace(existing_source: Optional[str], new_source: str) -> bool:
    if existing_source is None:
        return True
    return SOURCE_PRIORITY.get(new_source, 99) < SOURCE_PRIORITY.get(existing_source, 99)


def upsert_song(
    conn: sqlite3.Connection,
    song_id: str,
    title: str,
    artist: str,
    year: Optional[int],
    peak: Optional[int],
    weeks: Optional[int],
    source: str,
) -> None:
    cur = conn.cursor()
    cur.execute("SELECT source FROM songs WHERE song_id=?", (song_id,))
    row = cur.fetchone()
    if row and not should_replace(row[0], source):
        return
    tier, era = assign_lane(year, peak, source)
    cur.execute(
        """
        INSERT OR REPLACE INTO songs
            (song_id, title, artist, year, peak_position, weeks_on_chart, source, tier, era_bucket)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (song_id, title, artist, year, peak, weeks, source, tier, era),
    )


def upsert_lyrics(
    conn: sqlite3.Connection,
    lyrics_id: str,
    song_id: str,
    raw_text: str,
    clean_text: str,
    source: str,
) -> None:
    cur = conn.cursor()
    cur.execute("SELECT source FROM lyrics WHERE lyrics_id=?", (lyrics_id,))
    row = cur.fetchone()
    if row and not should_replace(row[0], source):
        return
    cur.execute(
        """
        INSERT OR REPLACE INTO lyrics
            (lyrics_id, song_id, raw_text, clean_text, source)
        VALUES (?, ?, ?, ?, ?);
        """,
        (lyrics_id, song_id, raw_text, clean_text, source),
    )


def ingest_kaggle_year_end(conn: sqlite3.Connection, csv_path: Path, log) -> int:
    count = 0
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row.get("Year") or row.get("year") or 0)
            except Exception:
                year = None
            title = row.get("Song") or row.get("song") or ""
            artist = row.get("Artist") or row.get("artist") or ""
            lyrics_raw = row.get("Lyrics") or row.get("lyrics") or ""
            if not (title and artist):
                continue
            song_id = slugify_song(title, artist, year)
            upsert_song(conn, song_id, title, artist, year, None, None, "kaggle_year_end")
            lyrics_id = f"{song_id}__kaggle"
            clean = clean_lyrics_text(lyrics_raw)
            upsert_lyrics(conn, lyrics_id, song_id, lyrics_raw, clean, "kaggle_year_end")
            count += 1
    conn.commit()
    log(f"[INFO] Ingested Kaggle Year-End rows: {count}")
    return count


def ingest_hot100_lyrics_audio(conn: sqlite3.Connection, csv_path: Path, log) -> int:
    count = 0
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("song") or row.get("titletext") or ""
            artist = row.get("band_singer") or row.get("artist") or ""
            if not (title and artist):
                continue
            try:
                year = int(row.get("year") or 0)
            except Exception:
                year = None
            try:
                peak = int(row.get("ranking") or 0)
            except Exception:
                peak = None
            lyrics_raw = row.get("lyrics") or ""
            weeks = None
            tempo_bpm = None
            duration_ms = None
            try:
                tempo_bpm = float(row.get("tempo")) if row.get("tempo") else None
            except Exception:
                tempo_bpm = None
            try:
                duration_ms = float(row.get("duration_ms")) if row.get("duration_ms") else None
            except Exception:
                duration_ms = None
            song_id = slugify_song(title, artist, year)
            upsert_song(conn, song_id, title, artist, year, peak, weeks, "hot100_lyrics_audio")
            lyrics_id = f"{song_id}__hot100"
            clean = clean_lyrics_text(lyrics_raw)
            upsert_lyrics(conn, lyrics_id, song_id, lyrics_raw, clean, "hot100_lyrics_audio")
            if tempo_bpm is not None or duration_ms is not None:
                conn.execute(
                    """
                    UPDATE features_song SET tempo_bpm=?, duration_sec=?
                    WHERE song_id=?;
                    """,
                    (tempo_bpm, duration_ms / 1000.0 if duration_ms else None, song_id),
                )
            count += 1
    conn.commit()
    log(f"[INFO] Ingested Hot100 lyrics+audio rows: {count}")
    return count


def ingest_fallback_top100(conn: sqlite3.Connection, csv_path: Path, log) -> int:
    count = 0
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("song") or row.get("Song Title") or row.get("title") or ""
            artist = row.get("artist") or row.get("Artist") or row.get("band_singer") or ""
            if not (title and artist):
                continue
            try:
                year = int(row.get("year") or row.get("Year") or 0)
            except Exception:
                year = None
            lyrics_raw = row.get("lyrics") or row.get("Lyrics") or ""
            song_id = slugify_song(title, artist, year)
            upsert_song(conn, song_id, title, artist, year, None, None, "top100_fallback")
            lyrics_id = f"{song_id}__fallback"
            clean = clean_lyrics_text(lyrics_raw)
            upsert_lyrics(conn, lyrics_id, song_id, lyrics_raw, clean, "top100_fallback")
            count += 1
    conn.commit()
    log(f"[INFO] Ingested fallback Top100 rows: {count}")
    return count


def ingest_billboard_spine(conn: sqlite3.Connection, csv_path: Path, log) -> int:
    count = 0
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title") or row.get("song") or ""
            artist = row.get("artist") or ""
            if not (title and artist):
                continue
            try:
                year = int(row.get("year") or 0)
            except Exception:
                year = None
            peak = None
            weeks = None
            try:
                peak = int(row.get("peak_position") or row.get("peak") or 0)
            except Exception:
                peak = None
            try:
                weeks = int(row.get("weeks_on_chart") or row.get("weeks") or 0)
            except Exception:
                weeks = None
            song_id = slugify_song(title, artist, year)
            upsert_song(conn, song_id, title, artist, year, peak, weeks, "ut_austin_billboard")
            count += 1
    conn.commit()
    log(f"[INFO] Ingested Billboard spine rows: {count}")
    return count

__all__ = [
    "ingest_billboard_spine",
    "ingest_fallback_top100",
    "ingest_hot100_lyrics_audio",
    "ingest_kaggle_year_end",
    "should_replace",
    "upsert_lyrics",
    "upsert_song",
]
