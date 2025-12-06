#!/usr/bin/env python3
"""
ma_clean_hci_layout.py

Normalize the visual layout and schema of .hci.json files under a root.

Target top-level order (when fields are present):

  1. HCI_v1
  2. HCI_v1_debug
  3. HCI_v1_final_score
  4. HCI_v1_final_tier
  5. HCI_v1_score
  6. HCI_v1_score_raw
  7. axes
  8. HCI_v1_interpretation
  9. HCI_v1_philosophy
 10. HCI_v1_notes

This script:
  - Preserves all existing numeric values for these fields.
  - Removes extra top-level keys like HCI_v1_is_hit_predictor, HCI_v1_metric_kind, etc.
  - Ensures HCI_v1_philosophy has the standard tagline/summary if present or missing.

Usage:
    python tools/ma_clean_hci_layout.py \
      --root features_output
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


PHILOSOPHY_DEFAULT = {
    "tagline": "The Top 40 of today is the Top 40 of ~40 years ago, re-parameterized.",
    "summary": (
        "HCI_v1 is a measure of Historical Echo — not a hit predictor. "
        "It describes how this audio's 6D axes align with the audio patterns "
        "of successful US Pop songs (~1985–2024) and does not guarantee future "
        "success or provide a \"hitness\" verdict. Trend and market_norm layers "
        "live on top of HCI_v1 as optimization advice for the current landscape; "
        "they never override or replace HCI_v1 scores."
    ),
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        # Maintain our chosen key order
        json.dump(obj, f, indent=2, sort_keys=False)


def normalize_philosophy(philos: Any) -> Dict[str, str]:
    """Ensure philosophy block has at least summary + tagline."""
    out: Dict[str, str] = {}
    if isinstance(philos, dict):
        if isinstance(philos.get("summary"), str) and philos["summary"].strip():
            out["summary"] = philos["summary"].strip()
        if isinstance(philos.get("tagline"), str) and philos["tagline"].strip():
            out["tagline"] = philos["tagline"].strip()

    # Fill any missing fields from default
    if "summary" not in out:
        out["summary"] = PHILOSOPHY_DEFAULT["summary"]
    if "tagline" not in out:
        out["tagline"] = PHILOSOPHY_DEFAULT["tagline"]

    return out


def clean_hci(path: Path) -> bool:
    try:
        data = load_json(path)
    except Exception as e:
        print(f"[WARN] Failed to read {path}: {e}")
        return False

    if not isinstance(data, dict):
        print(f"[WARN] HCI file {path} is not a JSON object, skipping")
        return False

    # Extract pieces we care about
    hci_v1 = data.get("HCI_v1")
    hci_debug = data.get("HCI_v1_debug")
    final_score = data.get("HCI_v1_final_score")
    final_tier = data.get("HCI_v1_final_tier")
    score = data.get("HCI_v1_score")
    score_raw = data.get("HCI_v1_score_raw")
    axes = data.get("axes")
    interp = data.get("HCI_v1_interpretation")
    philos_raw = data.get("HCI_v1_philosophy")
    notes = data.get("HCI_v1_notes")

    # Normalize philosophy block
    philos = normalize_philosophy(philos_raw) if philos_raw is not None else normalize_philosophy(None)

    # Build new ordered dict
    new_obj: Dict[str, Any] = {}

    if hci_v1 is not None:
        new_obj["HCI_v1"] = hci_v1
    if hci_debug is not None:
        new_obj["HCI_v1_debug"] = hci_debug
    if final_score is not None:
        new_obj["HCI_v1_final_score"] = final_score
    if final_tier is not None:
        new_obj["HCI_v1_final_tier"] = final_tier
    if score is not None:
        new_obj["HCI_v1_score"] = score
    if score_raw is not None:
        new_obj["HCI_v1_score_raw"] = score_raw
    if axes is not None:
        new_obj["axes"] = axes
    if isinstance(interp, str) and interp.strip():
        new_obj["HCI_v1_interpretation"] = interp.strip()
    # Philosophy is always present once we've run the injector
    new_obj["HCI_v1_philosophy"] = philos
    if isinstance(notes, str) and notes.strip():
        new_obj["HCI_v1_notes"] = notes.strip()

    try:
        save_json(path, new_obj)
        return True
    except Exception as e:
        print(f"[WARN] Failed to write {path}: {e}")
        return False


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Clean and normalize .hci.json layout (order, fields)."
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory (e.g. features_output)",
    )
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")

    hci_files = sorted(root.rglob("*.hci.json"))
    if not hci_files:
        print(f"[INFO] No .hci.json files found under {root}")
        return

    changed = 0
    for p in hci_files:
        if clean_hci(p):
            changed += 1

    print(f"[DONE] Processed {len(hci_files)} .hci.json files; rewrote {changed} of them.")


if __name__ == "__main__":
    main()
