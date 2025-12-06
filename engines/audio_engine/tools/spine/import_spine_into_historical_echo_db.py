#!/usr/bin/env python3
"""
Import Historical Spine v1 CSVs into the Historical Echo DB as table `spine_v1`.
Defaults resolve via ma_config (MA_SPINE_ROOT / MA_DATA_ROOT).
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Dict, Any

from ma_config.paths import get_historical_echo_db_path, get_spine_root


def load_core_spine(path: Path) -> Dict[str, Dict[str, Any]]:
    core: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["spine_track_id"]
            core[sid] = dict(row)
    return core


def load_audio_spine(path: Path) -> Dict[str, Dict[str, Any]]:
    audio: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["spine_track_id"]
            audio[sid] = dict(row)
    return audio


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Historical Spine v1 CSVs into historical_echo.db as table `spine_v1`"
    )
    parser.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="Path to Historical Echo engine SQLite DB",
    )
    parser.add_argument(
        "--spine-core",
        default=str(get_spine_root() / "spine_core_tracks_v1.csv"),
        help="Path to spine_core_tracks_v1.csv",
    )
    parser.add_argument(
        "--spine-audio",
        default=str(get_spine_root() / "spine_audio_spotify_v1.csv"),
        help="Path to spine_audio_spotify_v1.csv",
    )
    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    core_path = Path(args.spine_core).expanduser()
    audio_path = Path(args.spine_audio).expanduser()

    print(f"[INFO] Loading core spine: {core_path}")
    core = load_core_spine(core_path)

    print(f"[INFO] Loading audio spine: {audio_path}")
    audio = load_audio_spine(audio_path)

    print(f"[INFO] Connecting to DB: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS spine_v1")

    sample_core = next(iter(core.values()))
    sample_audio = next(iter(audio.values()))
    columns = list(sample_core.keys()) + [k for k in sample_audio.keys() if k != "spine_track_id"]
    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    cur.execute(f'CREATE TABLE spine_v1 ("spine_track_id" TEXT PRIMARY KEY, {col_defs})')

    rows = []
    for sid, cvals in core.items():
        avals = audio.get(sid, {})
        row = {"spine_track_id": sid}
        row.update(cvals)
        for k, v in avals.items():
            if k == "spine_track_id":
                continue
            row[k] = v
        rows.append([row.get(col, "") for col in ["spine_track_id"] + columns])

    placeholders = ", ".join("?" for _ in ["spine_track_id"] + columns)
    col_names = ", ".join(f'"{c}"' for c in ["spine_track_id"] + columns)
    cur.executemany(f"INSERT INTO spine_v1 ({col_names}) VALUES ({placeholders})", rows)
    conn.commit()
    conn.close()
    print(f"[DONE] Imported {len(rows)} rows into spine_v1.")


if __name__ == "__main__":
    main()
