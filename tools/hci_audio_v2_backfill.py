#!/usr/bin/env python3
"""
hci_audio_v2_backfill.py

Backfill HCI_audio_v2.raw into existing *.hci.json files by re-using the
audio_axes that are already stored there.

This is designed for the 100-song calibration / benchmark set (and any
other already-processed tracks) so we can start using HCI_audio_v2.raw
in the Historical Echo corpus and DB WITHOUT changing any v1 behaviour.

What it does:
- For each *.hci.json under one or more roots:
  - If HCI_audio_v2.raw already exists, it leaves the file alone.
  - Otherwise:
    - Reads audio_axes (dict or legacy list-of-6).
    - Computes a weighted mean using the audio_hci_v2 policy if present:
        datahub/cohorts/audio_hci_v2_policy_pop_us_2025Q4.json
      or falls back to internal default weights.
    - Writes:

        "HCI_audio_v2": {
          "raw": <float>,
          "policy": {
            "source": "...",
            "axis_weights": { ... }
          }
        }

Usage example:

    cd ~/music-advisor

    python tools/hci_audio_v2_backfill.py \
        --root features_output/2025/11/17

You can run this again later on other roots (e.g., WIP outputs) and it
will only fill files that don't already have HCI_audio_v2.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, List

from ma_config.audio import (
    DEFAULT_AUDIO_POLICY_PATH,
    resolve_audio_policy,
)


# Default weights (must match ma_simple_hci_from_features.py defaults)
DEFAULT_AUDIO_POLICY: Dict[str, Any] = {
    "axis_weights": {
        "TempoFit": 0.15,
        "RuntimeFit": 0.10,
        "LoudnessFit": 0.15,
        "Energy": 0.25,
        "Danceability": 0.20,
        "Valence": 0.15,
    }
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def normalize_axes(axes: Any) -> Optional[Dict[str, float]]:
    """
    Support both legacy list-of-6 and dict-of-named-axes schemas.

    We want TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence.
    If we can't get anything usable, return None.
    """
    if axes is None:
        return None

    # New schema: dict of axis_name -> value
    if isinstance(axes, dict):
        out: Dict[str, float] = {}
        for k, v in axes.items():
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
        return out if out else None

    # Legacy schema: list [TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence]
    if isinstance(axes, list):
        names = [
            "TempoFit",
            "RuntimeFit",
            "LoudnessFit",
            "Energy",
            "Danceability",
            "Valence",
        ]
        out: Dict[str, float] = {}
        for name, val in zip(names, axes):
            try:
                out[name] = float(val)
            except Exception:
                continue
        return out if out else None

    return None


def load_audio_policy(policy_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load audio HCI_v2 policy JSON if present.
    """
    try:
        text = policy_path.read_text()
    except FileNotFoundError:
        print(f"[WARN] Policy file not found: {policy_path} (using defaults)")
        return None
    except Exception as e:
        print(f"[WARN] Could not read policy file {policy_path}: {e} (using defaults)")
        return None

    try:
        conf = json.loads(text)
    except Exception as e:
        print(f"[WARN] Policy file {policy_path} is not valid JSON: {e} (using defaults)")
        return None

    node = conf.get("HCI_audio_v2") if isinstance(conf, dict) else None
    if isinstance(node, dict):
        return node

    print(f"[WARN] Policy file {policy_path} has no 'HCI_audio_v2' key (using defaults)")
    return None


def compute_hci_v2_raw(axes: Dict[str, float], policy: Optional[Dict[str, Any]]) -> float:
    """
    Compute HCI_audio_v2.raw as a weighted sum of the axes.

    If an external policy is provided, we use its axis_weights.
    Otherwise we fall back to DEFAULT_AUDIO_POLICY.
    """
    if policy and isinstance(policy, dict):
        weights = policy.get("axis_weights") or {}
    else:
        weights = {}

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
        num += w_f * float(axes[axis_name])
        denom += w_f

    if denom <= 0.0:
        # Defensive fallback: simple mean
        vals = list(axes.values())
        if not vals:
            return 0.0
        return float(sum(vals) / len(vals))

    return float(num / denom)


def backfill_root(root: Path, policy_path: Optional[Path]) -> None:
    """
    Scan a single root for *.hci.json files and backfill HCI_audio_v2
    where missing.
    """
    resolved_policy_path = policy_path or DEFAULT_AUDIO_POLICY_PATH
    policy_cfg = None
    _, cfg_from_env = resolve_audio_policy(resolved_policy_path, log=print)
    if cfg_from_env and isinstance(cfg_from_env, dict):
        policy_cfg = cfg_from_env.get("HCI_audio_v2") if "HCI_audio_v2" in cfg_from_env else cfg_from_env
    if policy_cfg is None:
        policy_cfg = load_audio_policy(resolved_policy_path)

    if policy_cfg is not None:
        policy_source = str(resolved_policy_path)
        axis_weights = policy_cfg.get("axis_weights") or DEFAULT_AUDIO_POLICY["axis_weights"]
    else:
        policy_source = "defaults_internal_v1"
        axis_weights = DEFAULT_AUDIO_POLICY["axis_weights"]

    total = 0
    updated = 0
    skipped_existing = 0
    skipped_no_axes = 0

    for hci_path in root.rglob("*.hci.json"):
        total += 1
        try:
            data = load_json(hci_path)
        except Exception as e:
            print(f"[WARN] Could not read {hci_path}: {e}")
            continue

        # If HCI_audio_v2 already exists with a raw value, skip this file
        existing_v2 = data.get("HCI_audio_v2")
        if isinstance(existing_v2, dict) and "raw" in existing_v2:
            skipped_existing += 1
            continue

        axes_raw = data.get("audio_axes")
        axes = normalize_axes(axes_raw)
        if not axes:
            skipped_no_axes += 1
            continue

        raw_v2 = compute_hci_v2_raw(axes, audio_policy)
        data["HCI_audio_v2"] = {
            "raw": round(raw_v2, 6),
            "policy": {
                "source": policy_source,
                "axis_weights": axis_weights,
            },
        }

        try:
            hci_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[WARN] Could not write back {hci_path}: {e}")
            continue

        updated += 1

    print(f"[INFO] Scanned root: {root}")
    print(f"[INFO]   total .hci.json files:         {total}")
    print(f"[INFO]   updated with HCI_audio_v2:      {updated}")
    print(f"[INFO]   skipped (already had v2):      {skipped_existing}")
    print(f"[INFO]   skipped (no usable audio_axes): {skipped_no_axes}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Backfill HCI_audio_v2.raw into existing .hci.json files using audio_axes."
    )
    ap.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root directory containing .hci.json files (can be passed multiple times).",
    )
    ap.add_argument(
        "--audio-policy",
        required=False,
        default=None,
        help="Audio axis weight policy JSON (defaults to env AUDIO_HCI_POLICY or calibration/hci_policy_pop_us_audio_v2.json).",
    )
    args = ap.parse_args()

    policy_path = Path(args.audio_policy).resolve() if args.audio_policy else None

    for root_str in args.root:
        root = Path(root_str).resolve()
        if not root.exists():
            print(f"[WARN] Root not found: {root}")
            continue
        backfill_root(root, policy_path)


if __name__ == "__main__":
    main()
