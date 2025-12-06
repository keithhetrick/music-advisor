#!/usr/bin/env python3
from __future__ import annotations

"""
hci_audio_v2_apply.py

Apply Audio HCI v2 calibration to *.hci.json files.

Given:
  - A calibration JSON produced by hci_audio_v2_fit.py
  - A root directory of *.hci.json files

We:

  - Read audio_axes for each track
  - Compute HCI_audio_v2.raw as a weighted sum of axes
  - Map raw -> score using a piecewise-linear quantile mapping
    defined by calibration["breakpoints_raw"] and ["breakpoints_target"]
  - Write:

      "HCI_audio_v2": {
        "raw": <float>,
        "score": <float>,
        "policy": { ... },
        "calibration": { ... }
      }

Usage
-----

  cd ~/music-advisor

  # Apply to the 100-song calibration set (for consistency)
  python tools/hci_audio_v2_apply.py \
    --root  features_output/2025/11/17 \
    --calib data/audio_hci_v2_calibration_pop_us_2025Q4.json

  # Apply to a WIP folder
  python tools/hci_audio_v2_apply.py \
    --root  features_output/2025/11/18 \
    --calib data/audio_hci_v2_calibration_pop_us_2025Q4.json
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import math

from ma_config.audio import (
    DEFAULT_AUDIO_POLICY_PATH,
    resolve_audio_policy,
    resolve_audio_v2_calibration,
)


def _iter_hci_files(root: Path):
    for p in root.rglob("*.hci.json"):
        if p.is_file():
            yield p


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)
        f.write("\n")


def _weighted_raw(audio_axes: Dict[str, Any], weights: Dict[str, float]) -> float:
    total = 0.0
    for name, w in weights.items():
        try:
            v = float(audio_axes.get(name, 0.0))
        except Exception:
            v = 0.0
        total += w * v
    return total


def _piecewise_linear(
    x: float,
    xs: List[float],
    ys: List[float],
) -> float:
    """
    Map x via piecewise-linear function defined by xs -> ys.

    xs and ys must have same length >= 2 and xs must be non-decreasing.

    - If x <= xs[0], return ys[0]
    - If x >= xs[-1], return ys[-1]
    - Otherwise, find interval [xs[i], xs[i+1]] with x in between and
      linearly interpolate between ys[i] and ys[i+1].
    """
    if not xs or not ys or len(xs) != len(ys):
        raise ValueError("Invalid breakpoints for piecewise_linear().")

    n = len(xs)
    if n == 1:
        return ys[0]

    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]

    # Find interval
    for i in range(n - 1):
        x0 = xs[i]
        x1 = xs[i + 1]
        if x0 <= x <= x1:
            y0 = ys[i]
            y1 = ys[i + 1]
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    # Fallback (should not happen)
    return ys[-1]


def cmd_apply(root: Path, calib_path: Path, policy_path: Path) -> None:
    """
    Apply HCI_audio_v2 to all *.hci.json under root.
    """
    _, calib = resolve_audio_v2_calibration(calib_path, log=print)
    if calib is None and calib_path.exists():
        calib = _load_json(calib_path)
    policy_path_resolved, policy_cfg = resolve_audio_policy(policy_path, log=print)
    if policy_cfg and isinstance(policy_cfg, dict) and "axis_weights" in policy_cfg:
        calib["axis_weights"] = policy_cfg["axis_weights"]
        calib.setdefault("policy_path", str(policy_path_resolved))
    scheme = calib.get("scheme", "audio_v2_quantile_piecewise_v1")
    axis_weights = calib.get("axis_weights") or {}
    breakpoints_raw = calib.get("breakpoints_raw") or []
    breakpoints_target = calib.get("breakpoints_target") or []
    set_name = calib.get("set_name", "")
    source_root = calib.get("source_root", "")

    if not axis_weights:
        raise SystemExit("[ERROR] Calibration has no axis_weights.")
    if not breakpoints_raw or not breakpoints_target:
        raise SystemExit("[ERROR] Calibration missing breakpoints.")
    if len(breakpoints_raw) != len(breakpoints_target):
        raise SystemExit("[ERROR] Calibration breakpoints_raw and breakpoints_target "
                        "must have same length.")

    print(f"[INFO] Using audio_v2 calibration from {calib_path}")
    print(f"[INFO] scheme={scheme}, set_name={set_name}")
    print(f"[INFO] axis_weights={axis_weights}")
    print(f"[INFO] breakpoints_raw={breakpoints_raw}")
    print(f"[INFO] breakpoints_target={breakpoints_target}")

    hci_files = list(_iter_hci_files(root))
    if not hci_files:
        print(f"[WARN] No *.hci.json files found under {root}")
        return

    print(f"[INFO] Applying audio_v2 to {len(hci_files)} file(s) under {root}")

    updated = 0
    skipped = 0

    for path in hci_files:
        try:
            hci = _load_json(path)
        except Exception as e:
            print(f"[WARN] Failed to read {path}: {e}")
            skipped += 1
            continue

        axes = hci.get("audio_axes") or {}
        if not isinstance(axes, dict):
            print(f"[WARN] {path} has non-dict audio_axes; skipping.")
            skipped += 1
            continue

        raw_v2 = _weighted_raw(axes, axis_weights)
        score_v2 = _piecewise_linear(float(raw_v2), breakpoints_raw, breakpoints_target)

        # Clamp defensively
        score_v2 = max(0.0, min(1.0, float(score_v2)))

        # Build HCI_audio_v2 payload
        audio_v2 = {
            "raw": raw_v2,
            "score": score_v2,
            "policy": {
                "source": "audio_hci_v2_policy_pop_us_2025Q4.json",
                "axis_weights": axis_weights,
            },
            "calibration": {
                "scheme": scheme,
                "breakpoints_raw": breakpoints_raw,
                "breakpoints_target": breakpoints_target,
                "set_name": set_name,
                "source_root": source_root,
                "raw_stats": calib.get("raw_stats", {}),
            },
        }

        hci["HCI_audio_v2"] = audio_v2

        try:
            _dump_json(path, hci)
            updated += 1
        except Exception as e:
            print(f"[WARN] Failed to write {path}: {e}")
            skipped += 1

    print(f"[DONE] Updated {updated} file(s); skipped {skipped}.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply Audio HCI v2 calibration to *.hci.json files."
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory to scan recursively for *.hci.json files.",
    )
    ap.add_argument(
        "--calib",
        required=False,
        default=None,
        help="Calibration JSON path produced by hci_audio_v2_fit.py (defaults to env AUDIO_HCI_V2_CALIBRATION or calibration/hci_audio_v2_calibration_pop_us_2025Q4.json).",
    )
    ap.add_argument(
        "--audio-policy",
        required=False,
        default=str(DEFAULT_AUDIO_POLICY_PATH),
        help="Audio axis weight policy JSON (defaults to env AUDIO_HCI_POLICY or calibration/hci_policy_pop_us_audio_v2.json).",
    )

    args = ap.parse_args()
    root = Path(args.root).resolve()
    calib_path = Path(args.calib).resolve() if args.calib else Path()
    policy_path = Path(args.audio_policy).resolve()

    cmd_apply(root, calib_path, policy_path)


if __name__ == "__main__":
    main()
