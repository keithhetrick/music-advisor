#!/usr/bin/env python3
"""
Lyric STT sidecar pipeline — audio -> transcript -> lyric_intel features/bridge export.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import (  # noqa: E402
    add_log_sandbox_arg,
    apply_log_sandbox_env,
    make_logger,
)
from ma_lyric_engine.lci import compute_lci_for_song  # noqa: E402
from ma_lyric_engine.utils import clean_lyrics_text  # noqa: E402
from ma_lyric_engine.features import (  # noqa: E402
    compute_features_for_song,
    load_concreteness_lexicon,
    load_vader,
    write_section_and_line_tables,
    write_song_features,
)
from ma_lyrics_engine.schema import ensure_schema  # noqa: E402
from ma_lyric_engine.export import export_bridge_payload  # noqa: E402
from ma_lyric_engine.ingest import upsert_lyrics, upsert_song  # noqa: E402
from ma_stt_engine.whisper_backend import (  # noqa: E402
    build_lyrics_from_segments,
    extract_vocals,
    transcribe_audio,
    transcribe_audio_alt,
)
from ma_config.profiles import (  # noqa: E402
    DEFAULT_LCI_CALIBRATION_PATH,
    DEFAULT_LCI_PROFILE,
    resolve_profile_config,
)
from ma_config.paths import get_lyric_intel_db_path  # noqa: E402


__all__ = [
    "process_wip",
    "parse_args",
    "main",
]


def process_wip(args, log) -> None:
    """
    Run audio -> STT -> lyric_intel features for a single WIP track.
    """
    audio_path = Path(args.audio).expanduser()
    if not audio_path.exists():
        raise SystemExit(f"[ERROR] Audio file not found: {audio_path}")

    db_path = Path(args.db).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)

    upsert_song(
        conn=conn,
        song_id=args.song_id,
        title=args.title or "",
        artist=args.artist or "",
        year=args.year,
        peak=None,
        weeks=None,
        source="wip_stt",
    )

    segments_path = Path(args.segments_file).expanduser() if getattr(args, "segments_file", None) else None
    transcript_path = Path(args.transcript_file).expanduser() if getattr(args, "transcript_file", None) else None
    raw_lyrics: str
    raw_lyrics_alt: str = ""
    if segments_path:
        if not segments_path.exists():
            raise SystemExit(f"[ERROR] Segments file not found: {segments_path}")
        with segments_path.open("r", encoding="utf-8", errors="ignore") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[ERROR] Failed to parse segments JSON: {exc}") from exc
        segments = data.get("segments", data) if isinstance(data, dict) else data
        raw_lyrics = build_lyrics_from_segments({"segments": segments, "text": ""})
        log(f"[INFO] Using provided segments file: {segments_path}")
    elif transcript_path:
        if not transcript_path.exists():
            raise SystemExit(f"[ERROR] Transcript file not found: {transcript_path}")
        raw_lyrics = transcript_path.read_text(encoding="utf-8", errors="ignore")
        log(f"[INFO] Using provided transcript file: {transcript_path}")
    else:
        chosen_audio = audio_path
        if not args.no_vocal_separation:
            chosen_audio = extract_vocals(audio_path, log)
        stt_result = transcribe_audio(chosen_audio, log)
        raw_lyrics = build_lyrics_from_segments(stt_result)
        if getattr(args, "run_alt_stt", False):
            stt_alt = transcribe_audio_alt(chosen_audio, log)
            raw_lyrics_alt = build_lyrics_from_segments(stt_alt)
            len_main = len(raw_lyrics.split())
            len_alt = len(raw_lyrics_alt.split())
            if len_alt > 0 and (len_main == 0 or len_alt > len_main * 1.05):
                log(f"[INFO] Selected alternate STT transcript (words: primary={len_main}, alt={len_alt})")
                raw_lyrics = raw_lyrics_alt
            else:
                log(f"[INFO] Kept primary STT transcript (words: primary={len_main}, alt={len_alt})")
    lyrics_id = f"{args.song_id}__wip_stt"
    clean_text = clean_lyrics_text(raw_lyrics)

    upsert_lyrics(
        conn=conn,
        lyrics_id=lyrics_id,
        song_id=args.song_id,
        raw_text=raw_lyrics,
        clean_text=clean_text,
        source="wip_stt",
    )
    if getattr(args, "run_alt_stt", False) and raw_lyrics_alt:
        clean_alt = clean_lyrics_text(raw_lyrics_alt)
        upsert_lyrics(
            conn=conn,
            lyrics_id=f"{args.song_id}__wip_stt_alt",
            song_id=args.song_id,
            raw_text=raw_lyrics_alt,
            clean_text=clean_alt,
            source="wip_stt_alt",
        )
    conn.commit()

    concreteness_lex = load_concreteness_lexicon(
        Path(args.concreteness_lexicon).expanduser() if args.concreteness_lexicon else None,
        log,
    )
    analyzer = load_vader()
    payload = compute_features_for_song(
        analyzer=analyzer,
        concreteness_lex=concreteness_lex,
        lyrics_id=lyrics_id,
        song_id=args.song_id,
        clean_text=clean_text,
        tempo_bpm=None,
        duration_ms=None,
    )
    write_section_and_line_tables(conn, payload, lyrics_id)
    write_song_features(conn, payload["features_song"])

    if not getattr(args, "skip_lci", False):
        lci_profile, calib_path, calibration = resolve_profile_config(
            cli_profile=getattr(args, "lci_profile", None),
            cli_config=getattr(args, "lci_calibration", None),
            env_profile_var="LYRIC_LCI_PROFILE",
            env_config_var="LYRIC_LCI_CALIBRATION",
            default_profile=DEFAULT_LCI_PROFILE,
            default_config_path=DEFAULT_LCI_CALIBRATION_PATH,
            log=log,
        )
        if calibration:
            computed = compute_lci_for_song(
                conn=conn,
                song_id=args.song_id,
                profile=lci_profile,
                calibration_path=calib_path,
                calibration=calibration,
                log=log,
            )
            if computed:
                log(f"[INFO] Computed LCI for song_id={args.song_id} using {calib_path}")
        else:
            log(f"[WARN] LCI calibration file not found; skipping LCI: {calib_path}")

    export = export_bridge_payload(conn, args.song_id, limit=1)
    out_json = json.dumps(export, indent=2)
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_json, encoding="utf-8")
        log(f"[INFO] Wrote lyric_intel bridge payload: {out_path}")
    else:
        print(out_json)
    conn.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Lyric STT sidecar for Lyric Intelligence Engine.")
    add_log_sandbox_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pw = sub.add_parser("process-wip", help="Process a WIP audio file into lyric_intel features.")
    pw.add_argument("--audio", required=True, help="Path to the WIP audio file.")
    pw.add_argument("--song-id", required=True, help="Unique song identifier for the WIP.")
    pw.add_argument("--title", help="Song title.", default="")
    pw.add_argument("--artist", help="Artist name.", default="")
    pw.add_argument("--year", type=int, help="Release year.", default=None)
    pw.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path (will be created).")
    pw.add_argument("--out", help="Output JSON path (default stdout).")
    pw.add_argument("--no-vocal-separation", action="store_true", help="Skip vocal isolation step.")
    pw.add_argument(
        "--concreteness-lexicon",
        help="Optional Brysbaert concreteness CSV (word, score) for concreteness scores.",
    )
    pw.add_argument(
        "--transcript-file",
        help="Optional plaintext transcript to skip STT; raw text will be ingested directly.",
    )
    pw.add_argument(
        "--segments-file",
        help="Optional JSON file containing Whisper-like segments [{'text': ...}] to skip STT.",
    )
    pw.add_argument(
        "--run-alt-stt",
        action="store_true",
        help="Run alternate STT (faster-whisper if available) and keep the better transcript.",
    )
    pw.add_argument(
        "--lci-calibration",
        default=None,
        help=f"LCI calibration JSON (defaults to env LYRIC_LCI_CALIBRATION or {DEFAULT_LCI_CALIBRATION_PATH}).",
    )
    pw.add_argument(
        "--skip-lci",
        action="store_true",
        help="Skip LCI computation even if calibration is available.",
    )
    pw.add_argument(
        "--lci-profile",
        default=None,
        help="LCI calibration profile label (metadata); defaults to env LYRIC_LCI_PROFILE or config profile.",
    )

    return ap.parse_args()


def main() -> None:
    args = parse_args()
    apply_log_sandbox_env(args)
    log = make_logger("lyric_stt_sidecar")
    if args.cmd == "process-wip":
        process_wip(args, log)
    else:
        raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
