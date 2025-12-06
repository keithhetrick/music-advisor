#!/usr/bin/env python3
"""
One-command lyric WIP pipeline: STT -> features/LCI/TTC -> neighbors.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional

from adapters.bootstrap import ensure_repo_root

# Ensure repo root and src/ on sys.path for module resolution
ensure_repo_root()

from adapters import add_log_sandbox_arg, apply_log_sandbox_env, make_logger  # noqa: E402
from ma_host.neighbors import nearest_neighbors  # noqa: E402
from ma_lyric_engine.schema import ensure_schema  # noqa: E402
from tools import lyric_stt_sidecar  # noqa: E402
from tools import ttc_sidecar  # noqa: E402
from ma_lyric_engine.export import export_bridge_payload  # noqa: E402
from ma_config.paths import get_lyric_intel_db_path  # noqa: E402
from ma_config.neighbors import resolve_neighbors_config  # noqa: E402


def run_pipeline(args, log) -> None:
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    bridge_path = out_dir / f"{args.song_id}_bridge.json"
    neighbors_path = out_dir / f"{args.song_id}_neighbors.json"

    # Step 1: STT sidecar
    stt_args = argparse.Namespace(
        audio=args.audio,
        song_id=args.song_id,
        title=args.title or "",
        artist=args.artist or "",
        year=args.year,
        db=args.db,
        out=str(bridge_path),
        no_vocal_separation=args.no_vocal_separation,
        concreteness_lexicon=args.concreteness_lexicon,
        transcript_file=args.transcript_file,
        segments_file=args.segments_file,
        run_alt_stt=args.run_alt_stt,
        lci_calibration=args.lci_calibration,
        skip_lci=args.skip_lci,
        lci_profile=args.lci_profile,
        cmd="process-wip",
    )
    lyric_stt_sidecar.process_wip(stt_args, log)

    # Step 1b: TTC sidecar to populate TTC and refresh bridge
    ttc_args = argparse.Namespace(
        db=args.db,
        song_id=args.song_id,
        section_pattern=None,
        profile=args.ttc_profile_label,
        out=None,
        cmd="estimate",
        seconds_per_section=args.ttc_seconds_per_section,
        ttc_profile=args.ttc_profile_path,
    )
    ttc_sidecar.run_estimate(ttc_args, log)

    # Refresh bridge to include TTC
    conn = sqlite3.connect(Path(args.db).expanduser())
    ensure_schema(conn)
    payload = export_bridge_payload(conn, args.song_id, limit=1)
    bridge_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    conn.close()

    # Step 2: neighbors (optional)
    neighbors_written = False
    if not args.skip_neighbors:
        db_path = Path(args.db).expanduser()
        conn = sqlite3.connect(db_path)
        ensure_schema(conn)
        limit, distance = resolve_neighbors_config(args.limit, args.distance, getattr(args, "neighbors_config", None))
        neighbors = nearest_neighbors(conn, song_id=args.song_id, limit=limit, distance=distance)
        payload = {"song_id": args.song_id, "count": len(neighbors), "items": neighbors}
        neighbors_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        conn.close()
        neighbors_written = True

    # Summary
    log(f"[INFO] Wrote bridge JSON: {bridge_path}")
    if neighbors_written:
        log(f"[INFO] Wrote neighbors JSON: {neighbors_path}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Lyric WIP pipeline: STT -> features/LCI/TTC -> neighbors.")
    add_log_sandbox_arg(ap)
    ap.add_argument("--audio", required=True, help="Path to WIP audio file.")
    ap.add_argument("--song-id", required=True, help="Unique song identifier for the WIP.")
    ap.add_argument("--title", default="", help="Song title.")
    ap.add_argument("--artist", default="", help="Artist name.")
    ap.add_argument("--year", type=int, default=None, help="Release year.")
    ap.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path.")
    ap.add_argument("--out-dir", default="features_output/lyrics", help="Output directory for JSON artifacts.")
    ap.add_argument("--limit", type=int, default=None, help="Neighbor count (default honors LYRIC_NEIGHBORS_LIMIT or config).")
    ap.add_argument("--distance", choices=["cosine", "euclidean"], default=None, help="Neighbor distance metric (default honors LYRIC_NEIGHBORS_DISTANCE or config).")
    ap.add_argument("--neighbors-config", help="Optional neighbors profile JSON (default honors LYRIC_NEIGHBORS_CONFIG or config/lyric_neighbors_default.json).")
    ap.add_argument("--skip-neighbors", action="store_true", help="Skip neighbor computation.")
    ap.add_argument("--no-vocal-separation", action="store_true", help="Skip vocal isolation step.")
    ap.add_argument("--concreteness-lexicon", help="Optional Brysbaert concreteness CSV for concreteness scores.")
    ap.add_argument("--transcript-file", help="Optional plaintext transcript to skip STT.")
    ap.add_argument("--segments-file", help="Optional JSON file containing Whisper-like segments to skip STT.")
    ap.add_argument("--run-alt-stt", action="store_true", help="Run alternate STT (faster-whisper) and keep the better transcript.")
    ap.add_argument("--lci-calibration", default=None, help="LCI calibration JSON path (default honors env LYRIC_LCI_CALIBRATION).")
    ap.add_argument("--lci-profile", default=None, help="LCI calibration profile label (default honors env LYRIC_LCI_PROFILE/config).")
    ap.add_argument("--skip-lci", action="store_true", help="Skip LCI computation.")
    ap.add_argument("--ttc-profile-path", default=None, help="TTC profile JSON path (default honors env LYRIC_TTC_CONFIG).")
    ap.add_argument("--ttc-profile-label", default=None, help="TTC profile label (default honors env LYRIC_TTC_PROFILE/config).")
    ap.add_argument("--ttc-seconds-per-section", type=float, default=12.0, help="Fallback seconds per section if no duration.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    apply_log_sandbox_env(args)
    log = make_logger("lyric_wip_pipeline")
    run_pipeline(args, log)


if __name__ == "__main__":
    main()
