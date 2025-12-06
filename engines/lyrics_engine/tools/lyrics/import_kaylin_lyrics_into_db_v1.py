from adapters.bootstrap import ensure_repo_root
#!/usr/bin/env python3
"""
import_kaylin_lyrics_into_db_v1.py

Import Kaylin Pavlik's Year-End Hot 100 lyrics dataset into historical_echo.db.

We:
  - Load Kaylin CSV (year, rank, song, artist, lyrics).
  - Match to the spine by (year, normalized song+artist).
  - Populate:
      * spine_lyrics_kaylin_v1  (full text)
      * spine_lyrics_metrics_v1 (word/line metrics)

Usage:

    mkdir -p tools/lyrics

    source .venv/bin/activate

    python tools/lyrics/import_kaylin_lyrics_into_db_v1.py \
      --db data/private/local_assets/historical_echo/historical_echo.db \
      --kaylin-csv data/private/local_assets/external/year_end/year_end_hot_100_lyrics_kaylin_1965_2015.csv \
      --reset
"""

import argparse
import csv
import os
import re
import sqlite3
from pathlib import Path

from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from adapters import add_log_sandbox_arg, apply_log_sandbox_env
from adapters import make_logger
from adapters import utc_now_iso
from ma_config.paths import get_historical_echo_db_path
from shared.config.paths import get_external_data_root
from security import db as sec_db


def norm_text(s: str) -> str:
    if s is None:
        return ""
    s = s.lower()
    s = re.sub(r"\b(feat\.?|ft\.?)\b", "", s)
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def make_slug(title: str, artist: str) -> str:
    return norm_text(title) + "___" + norm_text(artist)


def tokenize_words(text: str):
    if not text:
        return []
    # Very simple word tokenizer
    words = re.findall(r"[A-Za-z']+", text.lower())
    return words


def compute_lyrics_metrics(lyrics: str):
    if not lyrics:
        return {
            "word_count": 0,
            "unique_words": 0,
            "line_count": 0,
            "avg_words_per_line": 0.0,
        }
    lines = [ln for ln in lyrics.splitlines() if ln.strip()]
    line_count = len(lines) if lines else 0
    words = tokenize_words(lyrics)
    word_count = len(words)
    unique_words = len(set(words))
    avg_words_per_line = float(word_count) / line_count if line_count > 0 else 0.0
    return {
        "word_count": word_count,
        "unique_words": unique_words,
        "line_count": line_count,
        "avg_words_per_line": avg_words_per_line,
    }


def load_spine_map(conn):
    cur = conn.cursor()
    # Prefer spine_master_v1_lanes; fall back to spine_v1
    table = None
    for candidate in ("spine_master_v1_lanes", "spine_v1"):
        sec_db.safe_execute(cur, "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (candidate,))
        if cur.fetchone():
            table = sec_db.validate_table_name(candidate)
            break
    if not table:
        raise SystemExit(
            "[ERROR] Neither spine_master_v1_lanes nor spine_v1 found in DB."
        )

    _log(f"[INFO] Using spine table: {table}")
    cur = sec_db.safe_execute(conn, f"SELECT spine_track_id, year, artist, title FROM {table}")
    rows = cur.fetchall()

    # Map (year, slug) -> spine_track_id
    mapping = {}
    for spine_track_id, year, artist, title in rows:
        key = (int(year), make_slug(title or "", artist or ""))
        mapping[key] = spine_track_id
    _log(f"[INFO] Built spine map with {len(mapping)} entries")
    return mapping


def create_lyrics_tables(conn, reset=False):
    cur = conn.cursor()
    if reset:
        cur.execute("DROP TABLE IF EXISTS spine_lyrics_kaylin_v1")
        cur.execute("DROP TABLE IF EXISTS spine_lyrics_metrics_v1")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS spine_lyrics_kaylin_v1 (
            spine_track_id  TEXT PRIMARY KEY,
            year            INTEGER,
            rank_kaylin     INTEGER,
            song_kaylin     TEXT,
            artist_kaylin   TEXT,
            lyrics          TEXT,
            source          TEXT
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS spine_lyrics_metrics_v1 (
            spine_track_id      TEXT PRIMARY KEY,
            lyrics_provider     TEXT,
            word_count          INTEGER,
            unique_words        INTEGER,
            line_count          INTEGER,
            avg_words_per_line  REAL
        );
        """
    )

    conn.commit()


def main():
    ap = argparse.ArgumentParser(
        description="Import Kaylin Year-End lyrics into historical_echo.db."
    )
    ap.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="Path to SQLite DB (default honors MA_DATA_ROOT).",
    )
    ap.add_argument(
        "--kaylin-csv",
        default=str(get_external_data_root() / "year_end/year_end_hot_100_lyrics_kaylin_1965_2015.csv"),
        help="Kaylin lyrics CSV (default: data/private/local_assets/external/year_end/year_end_hot_100_lyrics_kaylin_1965_2015.csv)",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Drop/recreate lyrics tables before inserting.",
    )
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    ap.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)

    redact_env = os.getenv("LOG_REDACT", "0") == "1"
    redact_values_env = [v for v in (os.getenv("LOG_REDACT_VALUES") or "").split(",") if v]
    redact_flag = args.log_redact or redact_env
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or redact_values_env
    )
    global _log
    _log = make_logger("import_kaylin_lyrics", use_rich=False, redact=redact_flag, secrets=redact_values)

    db_path = Path(args.db)
    kaylin_path = Path(args.kaylin_csv)

    if not kaylin_path.is_file():
        raise SystemExit(f"[ERROR] Kaylin CSV not found: {kaylin_path}")

    _log(f"[INFO] Connecting to DB: {db_path}")
    conn = sqlite3.connect(db_path)

    spine_map = load_spine_map(conn)
    create_lyrics_tables(conn, reset=args.reset)

    _log(f"[INFO] Loading Kaylin lyrics from {kaylin_path} ...")
    matched = 0
    unmatched = 0

    cur = conn.cursor()

    with kaylin_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row.get("Year"))
            except Exception:
                continue

            song = row.get("Song", "")
            artist = row.get("Artist", "")
            lyrics = row.get("Lyrics", "")
            source = row.get("Source")
            rank = row.get("Rank")

            key = (year, make_slug(song, artist))
            spine_track_id = spine_map.get(key)

            if spine_track_id is None:
                unmatched += 1
                continue

            matched += 1
            # Insert full lyrics
            cur.execute(
                """
                INSERT OR REPLACE INTO spine_lyrics_kaylin_v1
                    (spine_track_id, year, rank_kaylin, song_kaylin,
                     artist_kaylin, lyrics, source)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    spine_track_id,
                    year,
                    int(rank) if rank else None,
                    song,
                    artist,
                    lyrics,
                    str(source) if source is not None else None,
                ),
            )

            # Metrics
            m = compute_lyrics_metrics(lyrics)
            cur.execute(
                """
                INSERT OR REPLACE INTO spine_lyrics_metrics_v1
                    (spine_track_id, lyrics_provider, word_count,
                     unique_words, line_count, avg_words_per_line)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    spine_track_id,
                    "kaylin_v1",
                    m["word_count"],
                    m["unique_words"],
                    m["line_count"],
                    m["avg_words_per_line"],
                ),
            )

    conn.commit()
    _log(f"[INFO] Lyrics import complete.")
    _log(f"[INFO] Matched   : {matched}")
    _log(f"[INFO] Unmatched : {unmatched}")

    conn.close()
    _log(f"[DONE] Finished at {utc_now_iso()}")


if __name__ == "__main__":
    main()
