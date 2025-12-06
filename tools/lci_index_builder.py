#!/usr/bin/env python3
"""
LCI builder CLI — delegates to ma_lyric_engine.lci utilities.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env, make_logger  # noqa: E402
from ma_lyrics_engine.lci import (  # noqa: E402
    build_calibration,
    compute_lci_for_song,
    iter_song_ids_for_scoring,
    load_calibration,
)
from ma_lyrics_engine.schema import ensure_schema  # noqa: E402
from ma_config.paths import get_lyric_intel_db_path  # noqa: E402


def run_score_songs(args, log) -> None:
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")
    calibration_path = Path(args.calibration).expanduser()
    if not calibration_path.exists():
        raise SystemExit(f"[ERROR] Calibration file not found: {calibration_path}")
    calibration = load_calibration(calibration_path)
    profile = args.profile or calibration.get("calibration_profile") or calibration.get("profile")
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    processed = 0
    for song_id in iter_song_ids_for_scoring(conn, args.song_id, args.limit):
        if compute_lci_for_song(
            conn,
            song_id=song_id,
            profile=profile,
            calibration=calibration,
            calibration_path=calibration_path,
            log=log,
        ):
            processed += 1
    log(f"[INFO] Scored LCI for songs: {processed}")
    conn.close()


def run_build_calibration(args, log) -> None:
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    build_calibration(
        conn=conn,
        core_csv=Path(args.core_csv).expanduser() if args.core_csv else None,
        profile=args.profile,
        out_path=Path(args.out).expanduser(),
        log=log,
    )
    conn.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Lyric Confidence Index builder.")
    add_log_sandbox_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)

    score = sub.add_parser("score-songs", help="Compute LCI for songs with existing lyric_intel features.")
    score.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path.")
    score.add_argument("--calibration", required=True, help="Calibration JSON file.")
    score.add_argument("--profile", default="us_pop", help="Calibration profile name.")
    score.add_argument("--song-id", help="Optional specific song_id to score.")
    score.add_argument("--limit", type=int, help="Optional limit on number of songs processed.")

    build = sub.add_parser("build-calibration", help="Build calibration JSON from a cohort.")
    build.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path.")
    build.add_argument("--core-csv", help="Optional core cohort CSV (title, artist, year).")
    build.add_argument("--out", required=True, help="Path to write calibration JSON.")
    build.add_argument("--profile", default="us_pop", help="Calibration profile name.")

    return ap.parse_args()


def main() -> None:
    args = parse_args()
    apply_log_sandbox_env(args)
    log = make_logger("lci_index_builder")
    if args.cmd == "score-songs":
        run_score_songs(args, log)
    elif args.cmd == "build-calibration":
        run_build_calibration(args, log)
    else:
        raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
