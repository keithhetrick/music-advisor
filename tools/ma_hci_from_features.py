#!/usr/bin/env python3
# tools/ma_hci_from_features.py
"""
Compute audio_axes + HCI_v1 from a single *.features.json file,
using existing hci_axes.compute_axes/compute_hci and your calibration JSON.

This is a thin, explicit wrapper so WIP tracks can be scored with the
same logic as your calibration cohorts, without involving an external LLM.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

# hci_axes.py lives in the same tools/ package
import hci_axes  # type: ignore
from ma_config.audio import (
    DEFAULT_HCI_CALIBRATION_PATH,
    DEFAULT_MARKET_NORMS_PATH,
    resolve_hci_calibration,
    resolve_market_norms,
)


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def apply_calibration(
    raw_hci: float,
    calib: Dict[str, Any] | None,
    anchor: str | None,
) -> Dict[str, Any]:
    """
    Apply a simple affine calibration based on the chosen anchor.
    For now, we treat WIP tracks as belonging to the '00_core_modern' anchor
    by default, which matches your core-modern calibration cohort.
    """
    out: Dict[str, Any] = {
        "HCI_v1_score_raw": round(float(raw_hci), 3),
    }

    if not calib or not anchor:
        # No calibration → raw score only
        out["HCI_v1_score"] = out["HCI_v1_score_raw"]
        out["calibration_anchor"] = None
        out["calibration_notes"] = "no calibration applied"
        return out

    anchors = calib.get("anchors", {})
    aconf = anchors.get(anchor)
    cap_min = calib.get("cap_min")
    cap_max = calib.get("cap_max")

    if not aconf:
        # Unknown anchor → fall back to raw
        out["HCI_v1_score"] = out["HCI_v1_score_raw"]
        out["calibration_anchor"] = None
        out["calibration_notes"] = f"anchor '{anchor}' not found; raw score only"
        return out

    scale = float(aconf.get("scale", 1.0))
    offset = float(aconf.get("offset", 0.0))
    calibrated = raw_hci * scale + offset

    # Optional global caps from calibration file
    if isinstance(cap_min, (int, float)):
        calibrated = max(float(cap_min), calibrated)
    if isinstance(cap_max, (int, float)):
        calibrated = min(float(cap_max), calibrated)

    out["HCI_v1_score"] = round(float(calibrated), 3)
    out["calibration_anchor"] = anchor
    out["calibration_notes"] = "affine calibration using anchor config"
    out["scale"] = scale
    out["offset"] = offset
    if "target_mean" in aconf and "raw_mean" in aconf:
        out["target_mean"] = float(aconf["target_mean"])
        out["raw_mean"] = float(aconf["raw_mean"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--features",
        required=True,
        help="Path to *.features.json (as written by ma_audio_features.py)",
    )
    ap.add_argument(
        "--market-norms",
        required=False,
        default=str(DEFAULT_MARKET_NORMS_PATH),
        help=(
            "Path to baseline JSON containing MARKET_NORMS "
            "(e.g. datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json)"
        ),
    )
    ap.add_argument(
        "--calibration",
        required=False,
        default=str(DEFAULT_HCI_CALIBRATION_PATH),
        help=(
            "Optional HCI calibration JSON "
            "(e.g. calibration/hci_calibration_pop_us_2025Q4.json)"
        ),
    )
    ap.add_argument(
        "--hci-profile",
        required=False,
        default=None,
        help="Optional HCI profile label (overrides env AUDIO_HCI_PROFILE).",
    )
    ap.add_argument(
        "--anchor",
        required=False,
        default="00_core_modern",
        help="Calibration anchor to use for WIP tracks (default: 00_core_modern)",
    )
    ap.add_argument(
        "--cap",
        type=float,
        default=None,
        help="Optional cap to pass through to hci_axes.compute_hci (e.g. 0.58)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output JSON path for HCI summary (e.g. <stem>.hci.json)",
    )
    args = ap.parse_args()

    # Load features
    features_blob = load_json(args.features)
    # Features may either be a flat dict or wrapped in {"features_full": {...}}
    if "features_full" in features_blob:
        features_full = features_blob["features_full"]
    else:
        features_full = features_blob

    # Load MARKET_NORMS
    norms_path, norms_cfg = resolve_market_norms(args.market_norms, log=print)
    baseline = norms_cfg or load_json(str(norms_path))
    market_norms = baseline.get("MARKET_NORMS", baseline.get("market_norms", {}))

    # Compute axes + raw HCI via existing logic
    audio_axes = hci_axes.compute_axes(features_full, market_norms)
    raw_hci = hci_axes.compute_hci(audio_axes, args.cap)

    # Optional calibration
    hci_profile, calib_path, calib_data = resolve_hci_calibration(args.hci_profile, args.calibration, log=print)
    if calib_data is None and calib_path and Path(calib_path).exists():
        calib_data = load_json(str(calib_path))
    hci_obj = apply_calibration(raw_hci, calib_data, args.anchor)

    out = {
        "audio_axes": audio_axes,
        "HCI_v1": hci_obj,
        "MARKET_NORMS_baseline_id": baseline.get("baseline_id")
        or baseline.get("cohort_id"),
        "region": baseline.get("region"),
        "profile": baseline.get("profile"),
        "HCI_profile": hci_profile,
        "market_norms_path": str(norms_path),
    }

    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"[ma_hci_from_features] wrote {args.out}")


if __name__ == "__main__":
    main()
