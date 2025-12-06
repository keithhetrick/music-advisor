#!/usr/bin/env python3
"""
Lyric Intelligence Engine CLI — delegates to ma_lyric_engine modules.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import os
from pathlib import Path
from typing import Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import (  # noqa: E402
    add_log_sandbox_arg,
    apply_log_sandbox_env,
    make_logger,
    utc_now_iso,
)
from ma_lyrics_engine.export import coverage_report, export_bridge_payload  # noqa: E402
from ma_config.paths import (  # noqa: E402
    get_core_1600_csv_path,
    get_hot100_lyrics_audio_path,
    get_kaggle_year_end_lyrics_path,
    get_lyric_intel_db_path,
)
from ma_lyrics_engine.features import (  # noqa: E402
    compute_features_for_song,
    load_concreteness_lexicon,
    load_vader,
    write_section_and_line_tables,
    write_song_features,
)
from ma_lyrics_engine.ingest import (  # noqa: E402
    should_replace,
    upsert_lyrics,
    upsert_song,
    ingest_billboard_spine,
    ingest_fallback_top100,
    ingest_hot100_lyrics_audio,
    ingest_kaggle_year_end,
)
from ma_lyric_engine.schema import ensure_schema  # noqa: E402


def run_export_bridge(args, log) -> None:
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    payload = export_bridge_payload(conn, args.song_id, args.limit)
    out_json = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
        log(f"[INFO] Wrote bridge export: {args.out} ({payload['count']} items)")
    else:
        print(out_json)


def run_phase_normalize(args, log) -> None:
    db_path = Path(args.db).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    if args.reset:
        conn.execute("DELETE FROM songs")
        conn.execute("DELETE FROM lyrics")
        conn.execute("DELETE FROM sections")
        conn.execute("DELETE FROM lines")
        conn.execute("DELETE FROM features_line")
        conn.execute("DELETE FROM features_song")
        conn.execute("DELETE FROM features_song_vector")
        conn.commit()
        log("[INFO] Reset lyric engine tables.")

    def check_path(label: str, path_str: Optional[str], required: bool = True) -> Optional[Path]:
        if not path_str:
            return None
        p = Path(path_str).expanduser()
        if not p.is_file():
            msg = f"[ERROR] {label} not found: {p}"
            if required:
                raise SystemExit(msg)
            log(msg)
            return None
        return p

    spine_path = check_path("Billboard spine", args.billboard_spine, required=bool(args.billboard_spine))
    kaggle_path = check_path(
        "Kaggle Year-End lyrics",
        args.kaggle_year_end or str(get_kaggle_year_end_lyrics_path()),
        required=False,
    )
    hot100_path = check_path(
        "Hot100 lyrics+audio",
        args.hot100_lyrics_audio or str(get_hot100_lyrics_audio_path()),
        required=False,
    )
    fallback_path = check_path("Fallback Top100", args.fallback_top100, required=False)

    if spine_path:
        ingest_billboard_spine(conn, spine_path, log)
    if kaggle_path:
        ingest_kaggle_year_end(conn, kaggle_path, log)
    if hot100_path:
        ingest_hot100_lyrics_audio(conn, hot100_path, log)
    if fallback_path:
        ingest_fallback_top100(conn, fallback_path, log)

    coverage_report(conn, Path(args.core_csv) if args.core_csv else None, log)
    log(f"[DONE] Phase 1 complete at {utc_now_iso()} -> {db_path}")


def run_phase_features(args, log) -> None:
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    concreteness_lex = load_concreteness_lexicon(Path(args.concreteness_lexicon) if args.concreteness_lexicon else None, log)
    analyzer = load_vader()
    cur = conn.cursor()
    cur.execute("SELECT lyrics_id, song_id, clean_text FROM lyrics")
    rows = cur.fetchall()
    total = len(rows)
    processed = 0
    for lyrics_id, song_id, clean_text in rows:
        payload = compute_features_for_song(
            analyzer,
            concreteness_lex,
            lyrics_id,
            song_id,
            clean_text or "",
            tempo_bpm=None,
            duration_ms=None,
        )
        write_section_and_line_tables(conn, payload, lyrics_id)
        write_song_features(conn, payload["features_song"])
        processed += 1
        if processed % 250 == 0:
            log(f"[INFO] Processed {processed}/{total} lyrics for features")
    log(f"[DONE] Phase 2+3 features complete ({processed} items)")


def parse_args() -> argparse.Namespace:
    os.environ.setdefault("LOG_REDACT", "1")
    ap = argparse.ArgumentParser(
        description="Lyric Intelligence Engine (normalize + feature extraction)."
    )
    add_log_sandbox_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("phase1-normalize", help="Normalize Billboard-aligned lyric corpora into SQLite.")
    p1.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path (will be created).")
    p1.add_argument("--billboard-spine", help="UT Austin rwd-billboard CSV (Hot100 weekly/BB200).")
    default_kaggle = get_kaggle_year_end_lyrics_path()
    p1.add_argument(
        "--kaggle-year-end",
        default=str(default_kaggle),
        help=f"Kaggle Year-End Hot 100 lyrics CSV (primary corpus). Defaults to env MA_KAGGLE_YEAR_END_LYRICS or {default_kaggle}.",
    )
    default_hot100 = get_hot100_lyrics_audio_path()
    p1.add_argument(
        "--hot100-lyrics-audio",
        default=str(default_hot100),
        help=f"Hot100 lyrics+audio metadata CSV (primary corpus). Defaults to env MA_HOT100_LYRICS_AUDIO or {default_hot100}.",
    )
    p1.add_argument("--fallback-top100", help="Fallback Top 100 songs+lyrics CSV (secondary).")
    default_core_csv = get_core_1600_csv_path()
    p1.add_argument(
        "--core-csv",
        default=str(default_core_csv),
        help=f"Core1600 CSV for coverage checks. Defaults to env MA_CORE1600_CSV or {default_core_csv}.",
    )
    p1.add_argument("--reset", action="store_true", help="Drop existing rows before ingest.")

    p2 = sub.add_parser(
        "phase2-features",
        help="Compute structural/diction/sentiment/POV + advanced rhyme/theme/concreteness features.",
    )
    p2.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path.")
    p2.add_argument(
        "--concreteness-lexicon",
        help="Optional Brysbaert concreteness CSV (word, score) for concreteness scores.",
    )

    p3 = sub.add_parser(
        "export-bridge",
        help="Export bridge-ready lyric_intel payloads (no raw lyrics) from SQLite.",
    )
    p3.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path.")
    p3.add_argument("--song-id", help="Optional single song_id to export.")
    p3.add_argument("--limit", type=int, default=100, help="Limit number of records when no song_id is provided.")
    p3.add_argument("--out", help="Output JSON path (default stdout).")

    return ap.parse_args()


def main() -> None:
    args = parse_args()
    apply_log_sandbox_env(args)
    log = make_logger("lyric_intel_engine")
    if args.cmd == "phase1-normalize":
        run_phase_normalize(args, log)
    elif args.cmd == "phase2-features":
        run_phase_features(args, log)
    elif args.cmd == "export-bridge":
        run_export_bridge(args, log)
    else:
        raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
