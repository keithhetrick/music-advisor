#!/usr/bin/env python3
# tools/ma_simple_hci_from_features.py
"""
Compute audio_axes + calibrated HCI_v1 from a single *.features.json file.

This version (v1.1, HCI_v2 planning-safe):
- Keeps the existing HCI_v1 behaviour intact:
  - Same six audio axes.
  - Same raw HCI_v1 = simple mean of axes.
  - Same calibration via calibration/hci_calibration_pop_us_2025Q4.json.
- Adds a *separate*, explicit HCI_audio_v2 raw score:
  - Weighted combination of the same axes.
  - Uses a small JSON policy if present:
      datahub/cohorts/audio_hci_v2_policy_pop_us_2025Q4.json
  - Falls back to built-in default weights when the policy file is missing.

Outputs a .hci.json with structure:

{
  "audio_axes": {
    "TempoFit": ...,
    "RuntimeFit": ...,
    "LoudnessFit": ...,
    "Energy": ...,
    "Danceability": ...,
    "Valence": ...
  },
  "HCI_v1_score_raw": ...,
  "HCI_v1_score": ...,
  "HCI_v1": {
    "raw": ...,
    "score": ...,
    "meta": { "calibration": {...} }
  },
  "HCI_audio_v2": {
    "raw": <float in [0,1]>,
    "score": <same as raw (for now)>,
    "policy": { "axis_weights": {...}, "policy_path": "<str or null>" }
  }
}

This file is deliberately simple and self-contained to make it easy to
evolve the audio_v2 policy without touching calibration logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

# from .utils import clamp01

def clamp01(x):
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

from tools.hci_axes import compute_axes
from tools.calibrate_hci import apply_calibration_to_raw, load_calibration
from ma_config.audio import (
    DEFAULT_AUDIO_POLICY_PATH,
    DEFAULT_HCI_CALIBRATION_PATH,
    DEFAULT_MARKET_NORMS_PATH,
    resolve_audio_policy,
    resolve_hci_calibration,
    resolve_market_norms,
)

# --------------------------------------------------------------------
# Paths and constants
# --------------------------------------------------------------------

DEFAULT_CALIBRATION_PATH = DEFAULT_HCI_CALIBRATION_PATH

DEFAULT_MARKET_NORMS: Dict[str, Any] = {
    "tempo_mean": 120.0,
    "tempo_std": 20.0,
    "duration_mean": 200.0,
    "duration_std": 40.0,
    "loudness_mean": -10.0,
    "loudness_std": 3.0,
}

# Core v2-planning policy: 4 "hard" axes, 2 "soft" axes.
DEFAULT_AUDIO_POLICY: Dict[str, Any] = {
    "axis_weights": {
        # 4 core / "hard" axes: strongest historical-echo anchors
        "TempoFit": 0.20,
        "RuntimeFit": 0.10,
        "LoudnessFit": 0.20,
        "Energy": 0.30,
        # 2 softer axes: still useful but intentionally down-weighted
        "Danceability": 0.12,
        "Valence": 0.08,
    }
}

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def load_features(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text())
    # Some pipelines wrap features inside a top-level "features_full" field
    if "features_full" in data:
        return data["features_full"]
    return data


def _validate_audio_policy(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate/clean an audio HCI_v2 policy block.

    The JSON, if present, is expected to look like:

    {
      "axis_weights": {
        "TempoFit": 0.22,
        "RuntimeFit": 0.10,
        "LoudnessFit": 0.22,
        "Energy": 0.28,
        "Danceability": 0.10,
        "Valence": 0.08
      }
    }

    If data is missing or invalid, DEFAULT_AUDIO_POLICY is used instead.
    """
    if not isinstance(raw, dict):
        return DEFAULT_AUDIO_POLICY
    axis_weights = raw.get("axis_weights")
    if not isinstance(axis_weights, dict):
        return DEFAULT_AUDIO_POLICY
    cleaned: Dict[str, float] = {}
    for k, v in axis_weights.items():
        try:
            vf = float(v)
        except Exception:
            continue
        if vf <= 0.0:
            continue
        cleaned[k] = vf
    if not cleaned:
        return DEFAULT_AUDIO_POLICY
    return {"axis_weights": cleaned}


def load_audio_policy(policy_path: Path) -> Dict[str, Any]:
    """
    Load optional audio HCI_v2 policy.

    If file is missing or invalid, DEFAULT_AUDIO_POLICY is used instead.
    """
    if not policy_path.exists():
        return DEFAULT_AUDIO_POLICY

    try:
        raw = json.loads(policy_path.read_text())
        return _validate_audio_policy(raw)
    except Exception:
        return DEFAULT_AUDIO_POLICY


def compute_audio_axes(features_full: Dict[str, Any], market_norms: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """
    Wrapper around hci_axes.compute_axes that returns a *dict* instead of a list.

    The canonical ordering in compute_axes is:
      [TempoFit, RuntimeFit, Energy, Danceability, Valence, LoudnessFit]

    We convert that into a named dict to be more robust against future
    re-ordering or axis expansion.
    """
    axes_list = compute_axes(features_full, market_norms or DEFAULT_MARKET_NORMS)
    if len(axes_list) != 6:
        raise ValueError(f"Expected 6 axes from compute_axes, got {len(axes_list)}")
    return {
        "TempoFit": axes_list[0],
        "RuntimeFit": axes_list[1],
        "Energy": axes_list[2],
        "Danceability": axes_list[3],
        "Valence": axes_list[4],
        "LoudnessFit": axes_list[5],
    }


def compute_hci_v1_from_axes(axes: Dict[str, float]) -> float:
    """
    Legacy HCI_v1 raw: simple mean of the six axes.

    This is intentionally kept stable for now so that existing calibration
    files remain valid. All v2 experimentation happens in HCI_audio_v2, not
    by changing this definition.
    """
    if not axes:
        return 0.0
    vals = [clamp01(v) for v in axes.values()]
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def compute_hci_audio_v2(axes: Dict[str, float], policy: Dict[str, Any]) -> float:
    """
    Compute HCI_audio_v2.raw as a weighted combination of axes.

    Weights come from:
      - policy["axis_weights"], if provided and valid
      - otherwise DEFAULT_AUDIO_POLICY["axis_weights"]

    The result is re-normalized into [0,1] by dividing by the sum of weights.
    """
    weights = policy.get("axis_weights") if isinstance(policy, dict) else None
    if not isinstance(weights, dict) or not weights:
        weights = DEFAULT_AUDIO_POLICY["axis_weights"]

    num = 0.0
    denom = 0.0

    for axis_name, w in weights.items():
        if axis_name not in axes:
            continue
        try:
            w_f = float(w)
        except Exception:
            continue
        if w_f <= 0.0:
            continue
        v = clamp01(axes.get(axis_name, 0.0))
        num += w_f * v
        denom += w_f

    if denom <= 0.0:
        return 0.0

    return clamp01(num / denom)


def build_hci_from_features(
    features_path: Path,
    calibration_path: Optional[Path] = None,
    audio_policy_path: Optional[Path] = None,
    market_norms_path: Optional[Path] = None,
    hci_profile: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Core worker: from a *.features.json path, produce an HCI dict.
    """
    if calibration_path is None:
        calibration_path = DEFAULT_CALIBRATION_PATH
    if audio_policy_path is None:
        audio_policy_path = DEFAULT_AUDIO_POLICY_PATH
    market_norms_path = market_norms_path or DEFAULT_MARKET_NORMS_PATH

    feats = load_features(features_path)
    # Market norms resolution
    norms_path_resolved, norms_cfg = resolve_market_norms(market_norms_path, log=print)
    market_norms = (norms_cfg or {}).get("MARKET_NORMS") or (norms_cfg or {}).get("market_norms") or DEFAULT_MARKET_NORMS

    axes = compute_audio_axes(feats, market_norms=market_norms)

    # Legacy v1 raw HCI: mean of the six axes
    hci_v1_raw = compute_hci_v1_from_axes(axes)

    # Calibrated v1 score
    hci_profile_resolved, calib_path_resolved, calib = resolve_hci_calibration(hci_profile, calibration_path, log=print)
    if calib is None and calib_path_resolved and Path(calib_path_resolved).exists():
        calib = load_calibration(calib_path_resolved)
    hci_v1_score = apply_calibration_to_raw(hci_v1_raw, calib)

    # Audio v2: weighted combination of axes
    policy_path_resolved, policy_cfg = resolve_audio_policy(audio_policy_path, log=print)
    audio_policy = _validate_audio_policy(policy_cfg or {}) if policy_cfg else load_audio_policy(policy_path_resolved)
    hci_audio_v2_raw = compute_hci_audio_v2(axes, audio_policy)

    feature_meta = feats.get("feature_pipeline_meta") or {}
    feature_meta = {
        "source_hash": feats.get("source_hash") or feature_meta.get("source_hash"),
        "config_fingerprint": feats.get("config_fingerprint") or feature_meta.get("config_fingerprint"),
        "pipeline_version": feats.get("pipeline_version") or feature_meta.get("pipeline_version"),
    }

    out: Dict[str, Any] = {
        "audio_axes": axes,
        "HCI_v1_score_raw": hci_v1_raw,
        "HCI_v1_score": hci_v1_score,
        "HCI_v1_final_score": hci_v1_score,
        "HCI_v1_role": "audio_hci_v1",
        "HCI_v1": {
            "raw": hci_v1_raw,
            "score": hci_v1_score,
            "meta": {
                "calibration": calib,
                "profile": hci_profile_resolved,
            },
        },
        "feature_pipeline_meta": feature_meta,
        "historical_echo_meta": {
            "calibration_path": str(calib_path_resolved),
            "calibration_profile": hci_profile_resolved,
            "final_source": "ma_simple_hci_from_features",
            "raw_score": hci_v1_raw,
            "calibrated_score": hci_v1_score,
            "HCI_v1_final_score": hci_v1_score,
        },
        "HCI_audio_v2": {
            "raw": hci_audio_v2_raw,
            "score": hci_audio_v2_raw,  # for now, same as raw (no extra calibration)
            "policy": {
                "axis_weights": audio_policy.get("axis_weights", {}),
                "policy_path": str(policy_path_resolved) if policy_path_resolved else None,
            },
        },
        "market_norms_path": str(norms_path_resolved),
    }
    return out


# --------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------

def main() -> None:
    import argparse

    p = argparse.ArgumentParser(
        description="Compute audio_axes + HCI_v1 (+ HCI_audio_v2) from a single *.features.json file."
    )
    p.add_argument(
        "--features",
        type=str,
        required=True,
        help="Path to input *.features.json",
    )
    p.add_argument(
        "--out",
        type=str,
        required=False,
        help="Optional output *.hci.json path. If omitted, prints to stdout.",
    )
    p.add_argument(
        "--calibration",
        type=str,
        required=False,
        default=str(DEFAULT_CALIBRATION_PATH),
        help="Path to calibration JSON (default honors env AUDIO_HCI_CALIBRATION).",
    )
    p.add_argument(
        "--hci-profile",
        type=str,
        required=False,
        default=None,
        help="Optional HCI profile label (overrides env AUDIO_HCI_PROFILE).",
    )
    p.add_argument(
        "--audio-policy",
        type=str,
        required=False,
        default=str(DEFAULT_AUDIO_POLICY_PATH),
        help="Optional audio_v2 policy JSON (defaults to env AUDIO_HCI_POLICY or calibration/hci_policy_pop_us_audio_v2.json).",
    )
    p.add_argument(
        "--market-norms",
        type=str,
        required=False,
        default=str(DEFAULT_MARKET_NORMS_PATH),
        help="Baseline market norms JSON (defaults to env AUDIO_MARKET_NORMS or calibration/market_norms_us_pop.json).",
    )
    args = p.parse_args()

    features_path = Path(args.features)
    out_path = Path(args.out) if args.out else None
    calib_path = Path(args.calibration) if args.calibration else None
    audio_policy_path = Path(args.audio_policy) if args.audio_policy else None
    market_norms_path = Path(args.market_norms) if args.market_norms else None

    result = build_hci_from_features(
        features_path=features_path,
        calibration_path=calib_path,
        audio_policy_path=audio_policy_path,
        market_norms_path=market_norms_path,
        hci_profile=args.hci_profile,
    )

    s = json.dumps(result, indent=2)
    if out_path:
        out_path.write_text(s)
    else:
        print(s)


if __name__ == "__main__":
    main()
