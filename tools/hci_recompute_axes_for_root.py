#!/usr/bin/env python3
# tools/hci_recompute_axes_for_root.py
"""Recompute the 6 canonical audio axes for all .hci.json files under a root.

This script is *non-destructive* with respect to scores:
- It rewrites only:
    - data["axes"][TempoFit, RuntimeFit, Energy, Danceability, Valence, LoudnessFit]
    - data["audio_axes"] (list in canonical order)
- It leaves any existing HCI_v1_score_raw / HCI_v1_score /
  HCI_v1_final_score and HCI_v1_role fields unchanged.

Use this when:
- You have updated hci_axes.compute_axes (e.g., new Valence design,
  fixed market norms handling), and
- You want your .hci.json axis values to reflect the current definition
  without disturbing previously calibrated scores.

Example:
    python tools/hci_recompute_axes_for_root.py \
      --root features_output/2025/11/17 \
      --market-norms calibration/market_norms_us_pop.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

import hci_axes  # type: ignore
from ma_config.audio import DEFAULT_MARKET_NORMS_PATH, resolve_market_norms

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env
from ma_audio_engine.adapters import utc_now_iso
from shared.ma_utils.logger_factory import get_configured_logger

_log = get_configured_logger("hci_recompute_axes")


AXES_ORDER: List[str] = [
    "TempoFit",
    "RuntimeFit",
    "Energy",
    "Danceability",
    "Valence",
    "LoudnessFit",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def load_market_norms(path: Path) -> Dict[str, Any]:
    """Load a market norms JSON.

    We pass the entire JSON object through to hci_axes.compute_axes, which
    now knows how to handle both flat and MARKET_NORMS-nested shapes.
    """
    return load_json(path)


def find_features_for_track(track_dir: Path) -> Path | None:
    """Return the first *.features.json in a track directory, if any."""
    for p in sorted(track_dir.glob("*.features.json")):
        return p
    return None


def recompute_axes_for_hci(hci_path: Path, market_norms: Dict[str, Any]) -> bool:
    """Recompute axes + audio_axes for a single .hci.json file.

    Returns True if the file was updated, False if skipped.
    """
    try:
        data = load_json(hci_path)
    except Exception as e:
        _log(f"[WARN] Failed to read {hci_path}: {e}")
        return False

    track_dir = hci_path.parent
    features_path = find_features_for_track(track_dir)
    if features_path is None:
        _log(f"[WARN] No *.features.json found for {hci_path}, skipping")
        return False

    try:
        feats_blob = load_json(features_path)
    except Exception as e:
        _log(f"[WARN] Failed to read features {features_path}: {e}")
        return False

    # Features may be flat or wrapped in {"features_full": {...}}
    if isinstance(feats_blob, dict) and "features_full" in feats_blob:
        features_full = feats_blob["features_full"]
    else:
        features_full = feats_blob

    if not isinstance(features_full, dict):
        _log(f"[WARN] Unexpected features format in {features_path}, skipping")
        return False

    # Compute new axes via current hci_axes logic.
    axes_list = hci_axes.compute_axes(features_full, market_norms)
    if not isinstance(axes_list, (list, tuple)) or len(axes_list) != 6:
        _log(f"[WARN] compute_axes() returned unexpected shape for {features_path}, skipping")
        return False

    # Build dict + list in canonical order.
    axes_dict = {name: float(val) for name, val in zip(AXES_ORDER, axes_list)}
    audio_axes = [float(val) for val in axes_list]

    # Patch into the existing HCI JSON without touching scores.
    if not isinstance(data, dict):
        _log(f"[WARN] HCI file {hci_path} is not a JSON object, skipping")
        return False

    data["axes"] = axes_dict
    data["audio_axes"] = audio_axes

    try:
        save_json(hci_path, data)
        return True
    except Exception as e:
        _log(f"[WARN] Failed to write {hci_path}: {e}")
        return False


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Recompute audio axes for all .hci.json files under a root."
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory (e.g. data/features_output/2025/11/17)",
    )
    ap.add_argument(
        "--market-norms",
        required=False,
        default=str(DEFAULT_MARKET_NORMS_PATH),
        help="Market norms JSON (default honors env AUDIO_MARKET_NORMS or shared/calibration/market_norms_us_pop.json)",
    )
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    ap.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    if args.log_redact:
        os.environ["LOG_REDACT"] = "1"
    if args.log_redact_values:
        os.environ["LOG_REDACT_VALUES"] = args.log_redact_values

    root = Path(args.root).expanduser().resolve()
    norms_path_resolved, market_norms_cfg = resolve_market_norms(args.market_norms, log=_log)
    norms_path = norms_path_resolved.expanduser().resolve()

    if not root.exists():
        ap.error(f"root does not exist: {root}")
    if not norms_path.exists():
        ap.error(f"market-norms does not exist: {norms_path}")

    market_norms = market_norms_cfg or load_market_norms(norms_path)

    hci_files = sorted(root.rglob("*.hci.json"))
    if not hci_files:
        _log(f"[INFO] No .hci.json files under {root}")
        return

    updated = 0
    total = 0
    for hci_path in hci_files:
        total += 1
        if recompute_axes_for_hci(hci_path, market_norms):
            updated += 1

    _log(f"[DONE] Processed {total} .hci.json files under {root}; updated {updated} of them. ts={utc_now_iso()}")


if __name__ == "__main__":
    main()
