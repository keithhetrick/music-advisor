#!/usr/bin/env python3
"""
Build artist metadata for spine from Spotify CSVs (env-driven paths).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from adapters.bootstrap import ensure_repo_root
from tools.audio.spine.common_paths import spine_root_override, spine_backfill_root_override

ensure_repo_root()


def main() -> None:
    ap = argparse.ArgumentParser(description="Build artist meta for spine from Spotify dumps.")
    ap.add_argument("--spine-root", help="Spine root (env MA_SPINE_ROOT or <data>/spine).")
    ap.add_argument("--spotify-csv", help="Spotify artist CSV (default under spine root).")
    ap.add_argument("--out", help="Output artist meta CSV (default under backfill root).")
    args = ap.parse_args()

    spine_root = spine_root_override(args.spine_root)
    backfill_root = spine_backfill_root_override(None)
    spotify_csv = Path(args.spotify_csv) if args.spotify_csv else spine_root / "spotify_artist_meta.csv"
    out_csv = Path(args.out) if args.out else backfill_root / "spine_artist_meta_from_spotify_v1.csv"

    if not spotify_csv.exists():
        raise SystemExit(f"[ERROR] Spotify CSV not found: {spotify_csv}")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with spotify_csv.open("r", encoding="utf-8", newline="") as f_in, out_csv.open("w", encoding="utf-8", newline="") as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames or [])
        writer.writeheader()
        writer.writerows(reader)
    print(f"[DONE] Wrote artist meta to {out_csv}")


if __name__ == "__main__":
    main()
