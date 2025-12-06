"""
calibrate_hci.py

Small helper module used by ma_simple_hci_from_features.py to turn a
raw audio HCI score into a calibrated 0–1 value using the same
'zscore_linear_v1' scheme as hci_calibration.py.

This does NOT replace tools/hci_calibration.py as a CLI; it’s just a
library-style helper.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ma_config.audio import DEFAULT_HCI_CALIBRATION_PATH


def clamp01(x: float) -> float:
    """Clamp a numeric value into [0.0, 1.0]."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _default_calibration_path() -> Path:
    """
    Default to the main US Pop v1 calibration JSON (see DEFAULT_HCI_CALIBRATION_PATH).
    """
    return DEFAULT_HCI_CALIBRATION_PATH


def load_calibration(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load a calibration JSON file.

    If `path` is None, use the default US Pop v1 calibration file.
    Returns a dict or None if the file does not exist or cannot be parsed.
    """
    if path is None:
        calib_path = _default_calibration_path()
    else:
        calib_path = Path(path)

    if not calib_path.is_file():
        print(
            f"[WARN] calibration file not found: {calib_path} "
            f"(raw scores will be clamped only)",
            file=sys.stderr,
        )
        return None

    try:
        with calib_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(
            f"[WARN] failed to load calibration file {calib_path}: {exc} "
            f"(raw scores will be clamped only)",
            file=sys.stderr,
        )
        return None

    # Minimal sanity check
    if "scheme" not in data:
        data["scheme"] = "zscore_linear_v1"

    return data


def apply_calibration_to_raw(
    raw_score: float,
    calib: Optional[Dict[str, Any]],
) -> float:
    """
    Apply a 'zscore_linear_v1' style calibration to a raw HCI score.

    If `calib` is None, simply clamp the raw score to [0, 1].
    """
    raw = float(raw_score)

    if calib is None:
        # No calibration available; just clamp.
        return clamp01(raw)

    scheme = calib.get("scheme", "zscore_linear_v1")

    if scheme == "zscore_linear_v1":
        raw_mean = float(calib.get("raw_mean", 0.5))
        raw_std = float(calib.get("raw_std", 0.15)) or 1.0
        target_mean = float(calib.get("target_mean", 0.70))
        target_std = float(calib.get("target_std", 0.18))

        z = (raw - raw_mean) / raw_std
        mapped = target_mean + z * target_std
        return clamp01(mapped)

    # Fallback: treat as identity + clamp.
    return clamp01(raw)


# Optional: tiny CLI for debugging, not used by Automator
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply HCI calibration to a single raw score."
    )
    parser.add_argument("raw", type=float, help="Raw HCI score (0–1)")
    parser.add_argument(
        "--calib",
        type=str,
        default=None,
        help="Path to calibration JSON (defaults to US Pop v1).",
    )
    args = parser.parse_args()

    calib = load_calibration(args.calib)
    out = apply_calibration_to_raw(args.raw, calib)
    print(f"raw={args.raw:.3f} -> calibrated={out:.3f}")
