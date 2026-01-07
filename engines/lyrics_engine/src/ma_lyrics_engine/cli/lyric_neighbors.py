#!/usr/bin/env python3
"""
Lyric neighbors CLI — finds nearest neighbors by cosine similarity over features_song_vector.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env, make_logger  # noqa: E402
from ma_host.neighbors import nearest_neighbors  # noqa: E402
from ma_lyrics_engine.schema import ensure_schema  # noqa: E402
from ma_config.paths import get_lyric_intel_db_path  # noqa: E402
from ma_config.neighbors import resolve_neighbors_config  # noqa: E402


def run_neighbors(args, log) -> None:
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    limit, distance = resolve_neighbors_config(args.limit, args.distance, getattr(args, "neighbors_config", None))
    neighbors = nearest_neighbors(conn, song_id=args.song_id, limit=limit, distance=distance)
    payload = {"song_id": args.song_id, "count": len(neighbors), "items": neighbors}
    out_json = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
        log(f"[INFO] Wrote neighbors payload: {args.out}")
    else:
        print(out_json)
    conn.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Lyric neighbors finder (cosine similarity).")
    add_log_sandbox_arg(ap)
    ap.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path.")
    ap.add_argument("--song-id", required=True, help="Target song_id to find neighbors for.")
    ap.add_argument("--limit", type=int, default=5, help="Number of neighbors to return.")
    ap.add_argument("--distance", choices=["cosine", "euclidean"], default="cosine", help="Similarity metric.")
    ap.add_argument(
        "--neighbors-config",
        help="Optional neighbors profile JSON (default honors env LYRIC_NEIGHBORS_CONFIG or config/lyric_neighbors_default.json).",
    )
    ap.add_argument("--out", help="Optional output JSON path.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    apply_log_sandbox_env(args)
    log = make_logger("lyric_neighbors")
    run_neighbors(args, log)


if __name__ == "__main__":
    main()
