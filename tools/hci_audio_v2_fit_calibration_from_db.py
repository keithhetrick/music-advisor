#!/usr/bin/env python3
"""
hci_audio_v2_fit_calibration_from_db.py

Fit a calibration mapping for HCI_audio_v2.raw using the anchor set stored
in historical_echo.db. This produces a JSON file describing a piecewise-
linear mapping from raw -> target [0,1] scores.

We DO NOT change any .hci.json files here. This only writes the
calibration spec. Another tool (hci_audio_v2_apply_calibration.py)
will actually apply it.

Typical usage:

    cd ~/music-advisor

    python tools/hci_audio_v2_fit_calibration_from_db.py \
        --db data/private/local_assets/historical_echo/historical_echo.db \
        --set-name 2025Q4_benchmark_100 \
        --only-calibration \
        --out calibration/hci_audio_v2_calibration_pop_us_2025Q4.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from math import floor, ceil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ma_config.audio import (
    DEFAULT_AUDIO_V2_CALIBRATION_PATH,
    resolve_audio_v2_calibration,
)
from ma_config.paths import get_historical_echo_db_path


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _quantile(values: Sequence[float], p: float) -> Optional[float]:
    """
    Simple quantile with linear interpolation. p in [0,1].
    """
    if not values:
        return None
    if p <= 0:
        return float(values[0])
    if p >= 1:
        return float(values[-1])

    n = len(values)
    pos = p * (n - 1)
    lo = floor(pos)
    hi = ceil(pos)

    if lo == hi:
        return float(values[int(pos)])

    w = pos - lo
    v_lo = float(values[lo])
    v_hi = float(values[hi])
    return (1.0 - w) * v_lo + w * v_hi


def _summary_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p10": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
            "max": None,
        }

    n = len(values)
    s = sum(values)
    mean = s / n
    var = sum((v - mean) ** 2 for v in values) / n if n > 0 else 0.0
    std = var ** 0.5

    sorted_vals = sorted(values)
    return {
        "count": n,
        "mean": mean,
        "std": std,
        "min": sorted_vals[0],
        "p10": _quantile(sorted_vals, 0.10),
        "p25": _quantile(sorted_vals, 0.25),
        "p50": _quantile(sorted_vals, 0.50),
        "p75": _quantile(sorted_vals, 0.75),
        "p90": _quantile(sorted_vals, 0.90),
        "max": sorted_vals[-1],
    }


def load_v2_raw(
    conn: sqlite3.Connection,
    set_name: Optional[str],
    only_calibration: bool,
) -> List[float]:
    """
    Fetch hci_audio_v2_raw values from hci_scores joined with tracks,
    optionally filtering by set_name and in_calibration_set=1.
    """
    conditions: List[str] = ["h.hci_audio_v2_raw IS NOT NULL"]
    params: List[Any] = []

    if set_name:
        conditions.append("t.set_name = ?")
        params.append(set_name)

    if only_calibration:
        conditions.append("t.in_calibration_set = 1")

    where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT h.hci_audio_v2_raw AS v
        FROM tracks t
        JOIN hci_scores h ON t.id = h.track_id
        {where_clause};
    """

    cur = conn.cursor()
    cur.execute(sql, params)
    vals: List[float] = []
    for row in cur.fetchall():
        try:
            vals.append(float(row["v"]))
        except Exception:
            continue
    return vals


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fit calibration mapping for HCI_audio_v2.raw from historical_echo.db."
    )
    ap.add_argument(
        "--db",
        required=False,
        default=str(get_historical_echo_db_path()),
        help="Path to historical_echo.db (default honors MA_DATA_ROOT).",
    )
    ap.add_argument(
        "--out",
        required=False,
        default=None,
        help="Output JSON path for audio_v2 calibration spec (default: env AUDIO_HCI_V2_CALIBRATION or calibration/hci_audio_v2_calibration_pop_us_2025Q4.json).",
    )
    ap.add_argument(
        "--set-name",
        help="Optional set_name filter (e.g. 2025Q4_benchmark_100).",
    )
    ap.add_argument(
        "--only-calibration",
        action="store_true",
        help="Restrict fitting to tracks where in_calibration_set = 1.",
    )
    ap.add_argument(
        "--region",
        default="US",
        help="Region label for this calibration (default: US).",
    )
    ap.add_argument(
        "--profile",
        default="Pop",
        help="Profile label for this calibration (default: Pop).",
    )

    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")

    conn = _connect(db_path)
    raw_vals = load_v2_raw(conn, args.set_name, args.only_calibration)
    conn.close()

    if not raw_vals:
        raise SystemExit("[ERROR] No hci_audio_v2_raw values found for given filters.")

    stats = _summary_stats(raw_vals)

    print(f"[INFO] Loaded {stats['count']} hci_audio_v2_raw values from {db_path}")
    if args.set_name:
        print(f"[INFO]   set_name: {args.set_name}")
    if args.only_calibration:
        print(f"[INFO]   only calibration set: True")

    # Log basic stats for sanity
    print("\n[HCI_audio_v2.raw stats]")
    print(f"  mean = {stats['mean']:.4f}")
    print(f"  std  = {stats['std']:.4f}")
    print(f"  min  = {stats['min']:.4f}")
    print(f"  p10  = {stats['p10']:.4f}")
    print(f"  p25  = {stats['p25']:.4f}")
    print(f"  p50  = {stats['p50']:.4f}")
    print(f"  p75  = {stats['p75']:.4f}")
    print(f"  p90  = {stats['p90']:.4f}")
    print(f"  max  = {stats['max']:.4f}")

    # Build piecewise mapping breakpoints:
    #  - min   -> 0.30
    #  - p10   -> 0.40
    #  - p25   -> 0.55
    #  - p50   -> 0.70   (median hit)
    #  - p75   -> 0.82
    #  - p90   -> 0.92
    #  - max   -> 0.98   (top-of-anchor cluster; we keep tiny headroom to 1.0)
    raw_breakpoints = [
        stats["min"],
        stats["p10"],
        stats["p25"],
        stats["p50"],
        stats["p75"],
        stats["p90"],
        stats["max"],
    ]

    if any(v is None for v in raw_breakpoints):
        raise SystemExit("[ERROR] Some required quantiles are None; not enough data?")

    target_breakpoints = [0.30, 0.40, 0.55, 0.70, 0.82, 0.92, 0.98]

    calib_spec = {
        "scheme": "audio_v2_quantile_piecewise_v1",
        "region": args.region,
        "profile": args.profile,
        "set_name": args.set_name,
        "source_db": str(db_path),
        "raw_stats": stats,
        "breakpoints": {
            "raw": raw_breakpoints,
            "target": target_breakpoints,
        },
    }

    if args.out:
        out_path = Path(args.out)
    else:
        out_path, _ = resolve_audio_v2_calibration(None, log=print)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(calib_spec, indent=2))

    print(f"\n[OK] Wrote audio_v2 calibration spec to {out_path}")


if __name__ == "__main__":
    main()
