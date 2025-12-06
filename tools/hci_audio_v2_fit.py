#!/usr/bin/env python3
from __future__ import annotations

"""
hci_audio_v2_fit.py

Fit Audio HCI v2 calibration from a benchmark cohort of *.hci.json files.

For each track in the calibration set, we:
  - Read audio_axes (TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence)
  - Compute a weighted sum (raw_v2)
  - Collect raw_v2 across the cohort
  - Compute quantile-based breakpoints and descriptive stats

We then write a calibration JSON, e.g.:

  data/audio_hci_v2_calibration_pop_us_2025Q4.json

Which contains:

  {
    "scheme": "audio_v2_quantile_piecewise_v1",
    "axis_weights": {...},
    "breakpoints_raw": [...],
    "breakpoints_target": [0.3, 0.4, 0.55, 0.7, 0.82, 0.92, 0.98],
    "set_name": "...",
    "source_root": "...",
    "raw_stats": {...}
  }

Usage
-----

  cd ~/music-advisor

  python tools/hci_audio_v2_fit.py \
    --root features_output/2025/11/17 \
    --out  data/audio_hci_v2_calibration_pop_us_2025Q4.json
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import math

from ma_config.audio import DEFAULT_AUDIO_POLICY_PATH, resolve_audio_policy

# Fixed axis weights for v2 (can be tuned via policy JSON/env).
DEFAULT_AXIS_WEIGHTS: Dict[str, float] = {
    "TempoFit": 0.15,
    "RuntimeFit": 0.10,
    "LoudnessFit": 0.15,
    "Energy": 0.25,
    "Danceability": 0.20,
    "Valence": 0.15,
}

# Target mapping breakpoints for quantile piecewise function.
DEFAULT_BREAKPOINTS_TARGET: List[float] = [0.3, 0.4, 0.55, 0.7, 0.82, 0.92, 0.98]


def _iter_hci_files(root: Path):
    for p in root.rglob("*.hci.json"):
        if p.is_file():
            yield p


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _weighted_raw(audio_axes: Dict[str, Any], weights: Dict[str, float]) -> float:
    """
    Compute weighted raw_v2 from audio_axes.
    Missing axes default to 0.0.
    """
    total = 0.0
    for name, w in weights.items():
        val = audio_axes.get(name)
        try:
            v = float(val)
        except Exception:
            v = 0.0
        total += w * v
    return total


def _percentile(sorted_values: List[float], q: float) -> float:
    """
    Simple percentile implementation (0 <= q <= 100).
    Uses linear interpolation between nearest ranks.
    """
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty list.")
    if q <= 0:
        return sorted_values[0]
    if q >= 100:
        return sorted_values[-1]

    k = (len(sorted_values) - 1) * (q / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def fit_calibration(
    root: Path,
    set_name: str,
    axis_weights: Dict[str, float],
    breakpoints_target: List[float],
) -> Dict[str, Any]:
    """
    Walk root, compute raw_v2 for each track, and fit calibration metadata.
    """
    raw_values: List[float] = []

    hci_files = list(_iter_hci_files(root))
    if not hci_files:
        raise SystemExit(f"[ERROR] No *.hci.json files found under {root}")

    print(f"[INFO] Fitting audio_v2 calibration from {len(hci_files)} files.")

    for path in hci_files:
        try:
            hci = _load_json(path)
        except Exception as e:
            print(f"[WARN] Failed to read {path}: {e}")
            continue

        axes = hci.get("audio_axes") or {}
        if not isinstance(axes, dict):
            print(f"[WARN] {path} has non-dict audio_axes; skipping.")
            continue

        rv2 = _weighted_raw(axes, axis_weights)
        raw_values.append(rv2)

    if not raw_values:
        raise SystemExit("[ERROR] No usable audio_axes found; cannot fit calibration.")

    raw_values.sort()
    n = len(raw_values)
    mean = sum(raw_values) / n
    var = sum((x - mean) ** 2 for x in raw_values) / max(1, (n - 1))
    std = math.sqrt(var)

    print(f"[INFO] raw_v2 stats: count={n}, mean={mean:.4f}, std={std:.4f}, "
          f"min={raw_values[0]:.4f}, max={raw_values[-1]:.4f}")

    # Choose quantile breakpoints for raw_v2.
    qs = [10.0, 20.0, 35.0, 50.0, 70.0, 90.0, 100.0]
    breakpoints_raw = [_percentile(raw_values, q) for q in qs]

    calib = {
        "scheme": "audio_v2_quantile_piecewise_v1",
        "axis_weights": axis_weights,
        "breakpoints_raw": breakpoints_raw,
        "breakpoints_raw_quantiles": qs,
        "breakpoints_target": breakpoints_target,
        "set_name": set_name,
        "source_root": str(root),
        "raw_stats": {
            "count": n,
            "mean": mean,
            "std": std,
            "min": raw_values[0],
            "max": raw_values[-1],
        },
    }
    return calib


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fit Audio HCI v2 calibration from a benchmark cohort."
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory of calibration *.hci.json files "
             "(e.g., features_output/2025/11/17).",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output JSON path for calibration "
             "(e.g., data/audio_hci_v2_calibration_pop_us_2025Q4.json).",
    )
    ap.add_argument(
        "--set-name",
        default="2025Q4_benchmark_100",
        help="Logical name for this calibration set.",
    )
    ap.add_argument(
        "--audio-policy",
        default=str(DEFAULT_AUDIO_POLICY_PATH),
        help="Axis weight policy JSON (defaults to env AUDIO_HCI_POLICY or calibration/hci_policy_pop_us_audio_v2.json).",
    )

    args = ap.parse_args()
    root = Path(args.root).resolve()
    out_path = Path(args.out).resolve()

    policy_path, policy_cfg = resolve_audio_policy(args.audio_policy, log=print)
    weights = DEFAULT_AXIS_WEIGHTS
    if policy_cfg and isinstance(policy_cfg, dict) and isinstance(policy_cfg.get("axis_weights"), dict):
        try:
            weights = {k: float(v) for k, v in policy_cfg["axis_weights"].items()}
        except Exception:
            weights = DEFAULT_AXIS_WEIGHTS

    calib = fit_calibration(
        root=root,
        set_name=args.set_name,
        axis_weights=weights,
        breakpoints_target=DEFAULT_BREAKPOINTS_TARGET,
    )
    calib["policy_path"] = str(policy_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(calib, f, indent=2, sort_keys=False)
        f.write("\n")

    print(f"[DONE] Wrote audio_v2 calibration to {out_path}")


if __name__ == "__main__":
    main()
