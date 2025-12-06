#!/usr/bin/env python3
from __future__ import annotations

"""
hci_assign_tiers.py

Role-aware tiering for HCI_v1_final_score.

Purpose
-------
Assign a human-readable tier label (HCI_v1_final_tier) to each *.hci.json file,
based on BOTH:

  - HCI_v1_role   (wip | benchmark | anchor | other)
  - HCI_v1_final_score  (0–1 float)

This fixes the problem where WIP tracks were being labeled
"S — Elite / Benchmark" even though their role is "wip".

Design
------
We use two different tier ladders:

1) Benchmark / anchor (production, catalog, calibration tracks)
   role in {"benchmark", "anchor"}:

   score >= 0.92  -> "S — Elite / Benchmark"
   score >= 0.80  -> "A — Strong / Hit-ready"
   score >= 0.65  -> "B — Solid / Competitive"
   score >= 0.50  -> "C — Developing / Niche"
   else           -> "D — Experimental / Off-norm"

2) WIP (drafts, worktapes, in-progress mixes)
   role == "wip":

   score >= 0.85  -> "WIP-S — Elite draft (close to benchmark zone)"
   score >= 0.70  -> "WIP-A — Strong draft"
   score >= 0.55  -> "WIP-B — Competitive draft"
   score >= 0.40  -> "WIP-C — Early draft / needs work"
   else           -> "WIP-D — Experimental / off-norm"

All other roles (or missing roles) default to the benchmark ladder.

The script updates both:
  - Top-level:      HCI_v1_final_tier
  - Inside HCI_v1:  HCI_v1["final_tier"] and HCI_v1["meta"]["tier"]

Usage
-----

  cd ~/music-advisor

  # Example: assign tiers for 100-song calibration set (benchmark role)
  python tools/hci_assign_tiers.py --root features_output/2025/11/17

  # Example: assign tiers for a WIP folder (WIP role already set by hci_final_score.py)
  python tools/hci_assign_tiers.py --root "features_output/2025/11/18"
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple, Optional


# -------------------------------------------------------------------
# Tier logic
# -------------------------------------------------------------------


def _get_score_and_role(hci: Dict[str, Any]) -> Tuple[Optional[float], str]:
    """
    Extract HCI_v1_final_score and HCI_v1_role from an .hci.json dict.

    If HCI_v1_final_score is missing, we fall back to HCI_v1["final_score"],
    if present. If role is missing, default to "benchmark".
    """
    score = hci.get("HCI_v1_final_score")
    if score is None:
        block = hci.get("HCI_v1") or {}
        score = block.get("final_score")

    role = hci.get("HCI_v1_role") or "benchmark"

    try:
        score_f = float(score) if score is not None else None
    except Exception:
        score_f = None

    return score_f, role


def _tier_for_benchmark(score: float) -> str:
    """
    Tier ladder for benchmark / anchor tracks.
    """
    if score >= 0.92:
        return "S — Elite / Benchmark"
    if score >= 0.80:
        return "A — Strong / Hit-ready"
    if score >= 0.65:
        return "B — Solid / Competitive"
    if score >= 0.50:
        return "C — Developing / Niche"
    return "D — Experimental / Off-norm"


def _tier_for_wip(score: float) -> str:
    """
    Tier ladder for WIP tracks.
    """
    if score >= 0.85:
        return "WIP-S — Elite draft (close to benchmark zone)"
    if score >= 0.70:
        return "WIP-A — Strong draft"
    if score >= 0.55:
        return "WIP-B — Competitive draft"
    if score >= 0.40:
        return "WIP-C — Early draft / needs work"
    return "WIP-D — Experimental / off-norm"


def assign_tier(score: float, role: str) -> str:
    """
    Decide tier string based on score and role.
    """
    role_lower = (role or "").lower()

    # Normalize role aliases if needed
    if role_lower in {"wip", "draft"}:
        return _tier_for_wip(score)

    # Treat anything else as benchmark-like
    return _tier_for_benchmark(score)


# -------------------------------------------------------------------
# IO helpers
# -------------------------------------------------------------------


def _iter_hci_files(root: Path):
    """
    Recursively yield *.hci.json files under root.
    """
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


# -------------------------------------------------------------------
# Main logic
# -------------------------------------------------------------------


def cmd_apply(root: Path) -> None:
    """
    Assign tiers to all .hci.json files under root.
    """
    hci_files = list(_iter_hci_files(root))
    if not hci_files:
        print(f"[WARN] No *.hci.json files found under {root}")
        return

    print(f"[INFO] Assigning tiers for {len(hci_files)} .hci.json file(s) under {root}")

    updated = 0
    skipped = 0

    # We'll capture cutpoints in meta for transparency.
    benchmark_cuts = {
        "S": 0.92,
        "A": 0.80,
        "B": 0.65,
        "C": 0.50,
        "D": 0.00,
    }
    wip_cuts = {
        "WIP-S": 0.85,
        "WIP-A": 0.70,
        "WIP-B": 0.55,
        "WIP-C": 0.40,
        "WIP-D": 0.00,
    }

    for path in hci_files:
        try:
            hci = _load_json(path)
        except Exception as e:
            print(f"[WARN] Failed to read {path}: {e}")
            skipped += 1
            continue

        score, role = _get_score_and_role(hci)
        if score is None:
            print(f"[WARN] {path} has no HCI_v1_final_score; skipping.")
            skipped += 1
            continue

        # Clamp defensively just in case
        score = max(0.0, min(1.0, score))
        tier = assign_tier(score, role)

        # Update top-level fields
        hci["HCI_v1_final_score"] = score
        hci["HCI_v1_role"] = role
        hci["HCI_v1_final_tier"] = tier

        # Update nested HCI_v1 block
        block = hci.get("HCI_v1") or {}
        block["final_score"] = score
        block["role"] = role
        block["final_tier"] = tier

        meta = block.get("meta") or {}
        meta["tier"] = {
            "source": "hci_assign_tiers_v1",
            "role_aware": True,
            "role": role,
            "cuts_benchmark": benchmark_cuts,
            "cuts_wip": wip_cuts,
        }
        block["meta"] = meta
        hci["HCI_v1"] = block

        try:
            _dump_json(path, hci)
            updated += 1
        except Exception as e:
            print(f"[WARN] Failed to write {path}: {e}")
            skipped += 1

    print(f"[DONE] Updated {updated} file(s); skipped {skipped}.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Assign role-aware HCI_v1_final_tier labels to *.hci.json files."
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory to scan recursively for *.hci.json files.",
    )

    args = ap.parse_args()
    root = Path(args.root).resolve()
    cmd_apply(root)


if __name__ == "__main__":
    main()
