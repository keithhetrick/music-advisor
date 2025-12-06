#!/usr/bin/env python3
"""
hci_audio_v2_apply_calibration.py

Apply a piecewise-linear calibration mapping (fitted by
hci_audio_v2_fit_calibration_from_db.py) to HCI_audio_v2.raw in
existing *.hci.json files.

For each *.hci.json:
  - If HCI_audio_v2.raw is missing, the file is skipped.
  - Otherwise, we compute:

        score = piecewise_linear(raw)

    and write:

        "HCI_audio_v2": {
          "raw": <existing raw>,
          "score": <calibrated>,
          "policy": { ... existing axis_weights ... },
          "calibration": {
            "scheme": "...",
            "breakpoints_raw": [...],
            "breakpoints_target": [...],
            "set_name": "...",
            "source_db": "...",
            "raw_stats": { ... }
          }
        }

We DO NOT touch any HCI_v1 fields. This is purely additive v2 metadata.

Usage example:

    cd ~/music-advisor

    python tools/hci_audio_v2_apply_calibration.py \
        --root features_output/2025/11/17 \
        --calib calibration/hci_audio_v2_calibration_pop_us_2025Q4.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ma_config.audio import (
    DEFAULT_AUDIO_V2_CALIBRATION_PATH,
    resolve_audio_v2_calibration,
)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def piecewise_linear_map(x: float, raw_bp: List[float], target_bp: List[float]) -> float:
    """
    Monotonic piecewise-linear mapping based on ordered breakpoints.

    raw_bp and target_bp must have the same length >= 2.
    """
    if not raw_bp or not target_bp or len(raw_bp) != len(target_bp):
        return x  # defensive no-op

    # Clamp to endpoints
    if x <= raw_bp[0]:
        return float(target_bp[0])
    if x >= raw_bp[-1]:
        return float(target_bp[-1])

    # Find segment
    for i in range(len(raw_bp) - 1):
        x0 = raw_bp[i]
        x1 = raw_bp[i + 1]
        if x0 <= x <= x1:
            y0 = target_bp[i]
            y1 = target_bp[i + 1]
            denom = (x1 - x0) if (x1 - x0) != 0 else 1e-9
            t = (x - x0) / denom
            return float(y0 + t * (y1 - y0))

    # Fallback (shouldn't happen if raw_bp sorted and x in range)
    return float(target_bp[-1])


def apply_to_root(root: Path, calib_spec: Dict[str, Any]) -> None:
    raw_bp = calib_spec.get("breakpoints", {}).get("raw") or []
    tgt_bp = calib_spec.get("breakpoints", {}).get("target") or []
    scheme = calib_spec.get("scheme", "audio_v2_quantile_piecewise_v1")

    set_name = calib_spec.get("set_name")
    source_db = calib_spec.get("source_db")
    raw_stats = calib_spec.get("raw_stats")

    updated = 0
    skipped_missing_v2 = 0
    total = 0

    for hci_path in root.rglob("*.hci.json"):
        total += 1
        try:
            data = load_json(hci_path)
        except Exception as e:
            print(f"[WARN] Could not read {hci_path}: {e}")
            continue

        v2 = data.get("HCI_audio_v2")
        if not isinstance(v2, dict) or "raw" not in v2:
            skipped_missing_v2 += 1
            continue

        try:
            raw_val = float(v2["raw"])
        except Exception:
            skipped_missing_v2 += 1
            continue

        score_val = piecewise_linear_map(raw_val, [float(x) for x in raw_bp], [float(y) for y in tgt_bp])

        # Preserve existing policy if present
        policy = v2.get("policy")
        if not isinstance(policy, dict):
            policy = None

        v2_updated: Dict[str, Any] = {
            "raw": raw_val,
            "score": round(score_val, 6),
        }

        if policy is not None:
            v2_updated["policy"] = policy

        v2_updated["calibration"] = {
            "scheme": scheme,
            "breakpoints_raw": raw_bp,
            "breakpoints_target": tgt_bp,
            "set_name": set_name,
            "source_db": source_db,
            "raw_stats": raw_stats,
        }

        data["HCI_audio_v2"] = v2_updated

        try:
            hci_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[WARN] Could not write back {hci_path}: {e}")
            continue

        updated += 1

    print(f"[INFO] Scanned root: {root}")
    print(f"[INFO]   total .hci.json files:            {total}")
    print(f"[INFO]   updated with HCI_audio_v2.score:  {updated}")
    print(f"[INFO]   skipped (no HCI_audio_v2.raw):    {skipped_missing_v2}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply HCI_audio_v2 calibration to existing .hci.json files."
    )
    ap.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root directory containing .hci.json files (can be passed multiple times).",
    )
    ap.add_argument(
        "--calib",
        required=False,
        default=None,
        help="Path to calibration JSON produced by hci_audio_v2_fit_calibration_from_db.py (defaults to env AUDIO_HCI_V2_CALIBRATION or calibration/hci_audio_v2_calibration_pop_us_2025Q4.json)",
    )

    args = ap.parse_args()

    calib_path = Path(args.calib).resolve() if args.calib else DEFAULT_AUDIO_V2_CALIBRATION_PATH
    calib_path_resolved, calib_spec = resolve_audio_v2_calibration(calib_path, log=print)
    if calib_spec is None and calib_path_resolved.exists():
        calib_spec = load_json(calib_path_resolved)
    if calib_spec is None:
        raise SystemExit(f"[ERROR] Calibration file not found: {calib_path_resolved}")

    for root_str in args.root:
        root = Path(root_str).resolve()
        if not root.exists():
            print(f"[WARN] Root not found: {root}")
            continue
        apply_to_root(root, calib_spec)


if __name__ == "__main__":
    main()
