#!/usr/bin/env python3
"""
CLI to build LCI/TTC lane norms JSON.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from adapters import add_log_sandbox_arg, apply_log_sandbox_env, make_logger  # noqa: E402
from ma_lyric_engine.schema import ensure_schema  # noqa: E402
from ma_lyric_engine.lci_norms import write_lane_norms  # noqa: E402
from ma_config.paths import get_lyric_intel_db_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build LCI/TTC lane norms JSON.")
    add_log_sandbox_arg(ap)
    ap.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path.")
    ap.add_argument("--profile", help="Calibration/profile label to filter on.", default=None)
    ap.add_argument("--out", required=True, help="Output JSON path for norms.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    apply_log_sandbox_env(args)
    log = make_logger("lyric_lci_norms")
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    norms = write_lane_norms(conn, args.profile, Path(args.out).expanduser())
    log(f"[INFO] Wrote lane norms ({len(norms.get('lanes', []))} lanes) to {args.out}")
    conn.close()


if __name__ == "__main__":
    main()
