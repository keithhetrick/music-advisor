#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import List


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build band thresholds for energy/danceability features "
                    "from truth_vs_ml CSV."
    )
    p.add_argument(
        "--csv",
        required=True,
        help="Path to truth_vs_ml CSV "
             "(e.g. calibration/aee_ml_reports/truth_vs_ml_v1_1.csv)",
    )
    p.add_argument(
        "--out",
        default="calibration/aee_band_thresholds_v1_1.json",
        help="Output JSON file for thresholds "
             "(default: calibration/aee_band_thresholds_v1_1.json)",
    )
    p.add_argument(
        "--energy-col",
        default="energy_feature",
        help="Column name for energy feature (default: energy_feature)",
    )
    p.add_argument(
        "--dance-col",
        default="danceability_feature",
        help="Column name for danceability feature (default: danceability_feature)",
    )
    p.add_argument(
        "--p-lo",
        type=float,
        default=0.30,
        help="Lower quantile for band split (default: 0.30)",
    )
    p.add_argument(
        "--p-hi",
        type=float,
        default=0.70,
        help="Upper quantile for band split (default: 0.70)",
    )
    return p.parse_args()


def read_numeric_column(csv_path: Path, col: str) -> List[float]:
    values: List[float] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = (row.get(col) or "").strip()
            if not raw:
                continue
            try:
                values.append(float(raw))
            except ValueError:
                continue
    return values


def quantile(values: List[float], q: float) -> float:
    """
    Simple linear interpolation quantile on sorted values.
    q in [0,1].
    """
    if not values:
        raise ValueError("quantile() called with empty list")
    xs = sorted(values)
    n = len(xs)
    if n == 1:
        return xs[0]
    q = max(0.0, min(1.0, q))
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] + (xs[hi] - xs[lo]) * frac


def build_threshold_block(
    col_name: str, values: List[float], p_lo: float, p_hi: float
) -> dict:
    lo_th = quantile(values, p_lo)
    hi_th = quantile(values, p_hi)
    return {
        "column": col_name,
        "p_lo": p_lo,
        "p_hi": p_hi,
        "threshold_lo": lo_th,
        "threshold_hi": hi_th,
        "stats": {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
        },
    }


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)

    if not csv_path.exists():
        raise SystemExit(f"[ERROR] CSV not found: {csv_path}")

    energy_vals = read_numeric_column(csv_path, args.energy_col)
    dance_vals = read_numeric_column(csv_path, args.dance_col)

    if not energy_vals:
        raise SystemExit(
            f"[ERROR] No numeric values found in column {args.energy_col!r}"
        )
    if not dance_vals:
        raise SystemExit(
            f"[ERROR] No numeric values found in column {args.dance_col!r}"
        )

    p_lo = float(args.p_lo)
    p_hi = float(args.p_hi)

    out = {
        "energy_feature": build_threshold_block(
            args.energy_col, energy_vals, p_lo, p_hi
        ),
        "danceability_feature": build_threshold_block(
            args.dance_col, dance_vals, p_lo, p_hi
        ),
        "meta": {
            "source_csv": str(csv_path),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "notes": "Auto-generated band thresholds for ML sanity & HCI calibration.",
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"[OK] Wrote thresholds to {out_path}")
    for key in ("energy_feature", "danceability_feature"):
        info = out[key]
        print(
            f"{key}: lo<{info['threshold_lo']:.6f}, "
            f"hi>{info['threshold_hi']:.6f} "
            f"(p_lo={info['p_lo']}, p_hi={info['p_hi']}, "
            f"count={info['stats']['count']})"
        )


if __name__ == "__main__":
    main()

