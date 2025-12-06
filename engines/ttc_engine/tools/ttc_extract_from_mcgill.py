#!/usr/bin/env python3
"""
Extract TTC (time-to-chorus) ground truth from the McGill Billboard corpus.

Inputs:
- Directory of annotation .txt files with timestamped section labels.
  Each line is expected to start with a timestamp (seconds or MM:SS) followed by a label.

Outputs:
- CSV or JSON rows with: song_id (optional), title, artist, ttc_seconds, source="McGill".
- Optional SQLite inserts into ttc_corpus_stats (sidecar TTC table).

Example row (JSON):
{
  "song_id": "Artist_-_Title",
  "title": "Title",
  "artist": "Artist",
  "ttc_seconds": 42.7,
  "source": "McGill",
  "path": "/root/annotations/Artist_-_Title.txt"
}
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from tools.ttc_init_db import CREATE_STATEMENTS  # type: ignore
except ImportError:
    from ttc_init_db import CREATE_STATEMENTS  # type: ignore

SOURCE = "McGill"
DATASET_NAME = "mcgill_billboard"


def _parse_timestamp(token: str) -> Optional[float]:
    """Accept plain seconds or MM:SS(.ms) tokens."""
    token = token.strip()
    if not token:
        return None
    try:
        if ":" in token:
            parts = token.split(":")
            val = 0.0
            for part in parts:
                val = val * 60 + float(part)
            return float(val)
        return float(token)
    except Exception:
        return None


def _find_first_chorus(path: Path) -> Optional[float]:
    """Return the first timestamp whose label contains 'chorus' (case-insensitive)."""
    try:
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if not parts:
                continue
            ts = _parse_timestamp(parts[0])
            label = " ".join(parts[1:]).lower()
            if "chorus" in label and ts is not None:
                return ts
    except Exception:
        return None
    return None


def _guess_title_artist(stem: str) -> tuple[str, str]:
    """
    Attempt to split filenames like Artist_-_Title.txt into artist/title.
    Falls back to stem as title with unknown artist.
    """
    separators = [" - ", "_-_", "__"]
    for sep in separators:
        if sep in stem:
            artist, title = stem.split(sep, 1)
            return title.strip() or stem, artist.strip()
    return stem, "Unknown"


def _ensure_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    # Only create TTC tables; CREATE IF NOT EXISTS keeps this idempotent.
    for stmt in CREATE_STATEMENTS:
        cur.execute(stmt)
    conn.commit()


def _upsert_corpus_rows(conn: sqlite3.Connection, rows: Iterable[Dict[str, object]]) -> int:
    _ensure_tables(conn)
    cur = conn.cursor()
    written = 0
    for row in rows:
        cur.execute(
            """
            INSERT INTO ttc_corpus_stats (
                dataset_name, dataset_song_id, title, artist, year, slug,
                ttc_seconds, ttc_beats, ttc_bars, chorus_label_used
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dataset_name, dataset_song_id) DO UPDATE SET
                title=excluded.title,
                artist=excluded.artist,
                year=excluded.year,
                slug=excluded.slug,
                ttc_seconds=excluded.ttc_seconds,
                ttc_beats=excluded.ttc_beats,
                ttc_bars=excluded.ttc_bars,
                chorus_label_used=excluded.chorus_label_used;
            """,
            (
                DATASET_NAME,
                row.get("song_id"),
                row.get("title"),
                row.get("artist"),
                row.get("year"),
                row.get("slug"),
                row.get("ttc_seconds"),
                row.get("ttc_beats"),
                row.get("ttc_bars"),
                row.get("chorus_label_used"),
            ),
        )
        written += 1
    conn.commit()
    return written


def extract_rows(root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for path in sorted(root.glob("**/*.txt")):
        ttc = _find_first_chorus(path)
        title, artist = _guess_title_artist(path.stem)
        rows.append(
            {
                "song_id": path.stem,
                "title": title,
                "artist": artist,
                "ttc_seconds": ttc,
                "source": SOURCE,
                "dataset_name": DATASET_NAME,
                "ttc_beats": None,
                "ttc_bars": None,
                "chorus_label_used": "chorus" if ttc is not None else "none",
                "slug": None,
                "year": None,
                "path": str(path),
            }
        )
    return rows


def write_csv(out: Path, rows: Iterable[Dict[str, object]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    rows_list = list(rows)
    fieldnames = [
        "song_id",
        "title",
        "artist",
        "ttc_seconds",
        "ttc_beats",
        "ttc_bars",
        "chorus_label_used",
        "source",
        "dataset_name",
        "slug",
        "year",
        "path",
    ]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_list:
            writer.writerow(row)


def write_json(out: Path, rows: Iterable[Dict[str, object]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    rows_list = list(rows)
    out.write_text(json.dumps(rows_list, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Extract TTC from McGill Billboard annotations.")
    ap.add_argument("--mcgill-dir", required=True, help="Root directory of McGill annotation .txt files.")
    ap.add_argument("--out", help="Output CSV/JSON path.")
    ap.add_argument("--db", help="Optional SQLite DB path to upsert into ttc_corpus_stats.")
    ap.add_argument("--json", action="store_true", help="Write JSON instead of CSV.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.mcgill_dir).expanduser()
    if not root.exists():
        raise SystemExit(f"Input directory does not exist: {root}")
    if not args.out and not args.db:
        raise SystemExit("Provide --out for CSV/JSON export and/or --db for SQLite insert.")

    rows = extract_rows(root)
    db_written: Optional[int] = None
    if args.db:
        db_path = Path(args.db).expanduser()
        conn = sqlite3.connect(db_path)
        db_written = _upsert_corpus_rows(conn, rows)
        conn.close()
    if args.out:
        out_path = Path(args.out)
        if args.json or args.out.lower().endswith(".json"):
            write_json(out_path, rows)
        else:
            write_csv(out_path, rows)
    msg_parts: List[str] = [f"rows={len(rows)}"]
    if args.out:
        msg_parts.append(f"file={args.out}")
    if db_written is not None:
        msg_parts.append(f"db_rows={db_written}")
        msg_parts.append(f"db={args.db}")
    print(f"[ttc_extract_from_mcgill] {' '.join(msg_parts)}")


if __name__ == "__main__":
    main()
