#!/usr/bin/env python3
"""
CLI to build a unified song_context JSON from audio + lyric bundles.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import sys

from ma_host.song_context import build_song_context
from ma_host.contracts import SONG_CONTEXT_KEYS, META_FIELDS
from ma_lyric_engine.bundle import build_bundle as build_lyric_bundle
from ma_config.paths import get_lyric_intel_db_path
from ma_config.neighbors import resolve_neighbors_config
from ma_lyric_engine.export import export_bridge_payload
from ma_lyric_engine.schema import ensure_schema
from ma_host.neighbors import nearest_neighbors
import sqlite3


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    default_lyric_db = get_lyric_intel_db_path()
    ap = argparse.ArgumentParser(description="Build song_context JSON from audio + lyric bundles.")
    ap.add_argument("--audio-bundle", help="Optional audio bundle JSON path.")
    ap.add_argument("--lyric-bridge", help="Lyric bridge JSON path.")
    ap.add_argument("--lyric-neighbors", help="Lyric neighbors JSON path.")
    ap.add_argument(
        "--lyric-db",
        help=f"Optional SQLite DB to auto-fetch lyric bridge/neighbors (defaults to env LYRIC_INTEL_DB or {default_lyric_db}).",
    )
    ap.add_argument(
        "--neighbors-config",
        help="Optional neighbors profile JSON (default honors LYRIC_NEIGHBORS_CONFIG or config/lyric_neighbors_default.json).",
    )
    ap.add_argument(
        "--neighbors-distance",
        choices=["cosine", "euclidean"],
        default=None,
        help="Neighbor distance metric (default honors LYRIC_NEIGHBORS_DISTANCE or config).",
    )
    ap.add_argument(
        "--neighbors-limit",
        type=int,
        default=None,
        help="Neighbor count (default honors LYRIC_NEIGHBORS_LIMIT or config).",
    )
    ap.add_argument("--out", required=True, help="Output song_context JSON path.")
    ap.add_argument("--song-id", required=True, help="Song ID (meta).")
    ap.add_argument("--title", default="", help="Title (meta).")
    ap.add_argument("--artist", default="", help="Artist (meta).")
    ap.add_argument("--year", type=int, default=None, help="Year (meta).")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    audio_bundle = load_json(Path(args.audio_bundle).expanduser()) if args.audio_bundle else None
    lyric_bundle = None
    if args.lyric_bridge and args.lyric_neighbors:
        bridge = load_json(Path(args.lyric_bridge).expanduser())
        neighbors = load_json(Path(args.lyric_neighbors).expanduser())
        lyric_bundle = build_lyric_bundle(bridge, neighbors)
    elif args.lyric_db:
        db_path = Path(args.lyric_db or get_lyric_intel_db_path()).expanduser()
        conn = sqlite3.connect(db_path)
        ensure_schema(conn)
        limit, distance = resolve_neighbors_config(args.neighbors_limit, args.neighbors_distance, args.neighbors_config)
        bridge = export_bridge_payload(conn, args.song_id, limit=1)
        neighbors = nearest_neighbors(conn, song_id=args.song_id, limit=limit, distance=distance)
        lyric_bundle = build_lyric_bundle(bridge, {"count": len(neighbors), "items": neighbors})
        conn.close()

    meta = {"song_id": args.song_id, "title": args.title, "artist": args.artist, "year": args.year}
    song_context = build_song_context(meta=meta, audio_bundle=audio_bundle, lyric_bundle=lyric_bundle)
    # Basic contract assertion to catch structural drift early
    missing_meta = META_FIELDS - set(song_context.get("meta", {}).keys())
    missing_top = SONG_CONTEXT_KEYS - set(song_context.keys())
    if missing_meta or missing_top:
        print(f"[WARN] song_context missing fields; meta_missing={missing_meta}, top_missing={missing_top}", file=sys.stderr)
    out_path = Path(args.out).expanduser()
    out_path.write_text(json.dumps(song_context, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
