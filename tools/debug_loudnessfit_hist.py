#!/usr/bin/env python3
"""
tools/debug_loudnessfit_hist.py

Inspect the distribution of HCI_v1 LoudnessFit across a features_output
tree and print a simple text histogram.

Usage:

  python tools/debug_loudnessfit_hist.py \
    --root features_output/2025/11/22 \
    --years 1985 1986
"""

import argparse
import json
from pathlib import Path
from typing import List, Optional, Sequence


def collect_loudnessfit(
    root: Path,
    years_filter: Optional[Sequence[int]] = None,
) -> List[float]:
    years_set = set(int(y) for y in years_filter) if years_filter else None
    vals: List[float] = []

    for hci_path in root.rglob("*.hci.json"):
        # Infer year from path: root/<year>/...
        rel = hci_path.relative_to(root)
        parts = rel.parts
        if not parts:
            continue

        try:
            year = int(parts[0])
        except Exception:
            year = None

        if years_set is not None and year not in years_set:
            continue

        try:
            data = json.loads(hci_path.read_text())
        except Exception:
            continue

        axes = None
        if "HCI_v1" in data and isinstance(data["HCI_v1"], dict):
            axes = data["HCI_v1"].get("axes") or data.get("axes")
        else:
            axes = data.get("axes")

        if not isinstance(axes, dict):
            continue

        lf = axes.get("LoudnessFit")
        if isinstance(lf, (int, float)):
            vals.append(float(lf))

    return vals


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Print a text histogram of LoudnessFit across .hci.json files."
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root of features_output tree (e.g. features_output/2025/11/22)",
    )
    ap.add_argument(
        "--years",
        nargs="*",
        type=int,
        help="Optional list of years to include (e.g. 1985 1986). "
             "If omitted, include all years under root.",
    )
    ap.add_argument(
        "--bins",
        type=int,
        default=5,
        help="Number of bins between 0.0 and 1.0 (default: 5)",
    )
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"[ERROR] root does not exist: {root}")

    vals = collect_loudnessfit(root, args.years)

    if not vals:
        raise SystemExit("[ERROR] No LoudnessFit values found.")

    n = len(vals)
    vmin = min(vals)
    vmax = max(vals)
    mean_val = sum(vals) / n

    print("=== LoudnessFit distribution ===")
    if args.years:
        print(f"Years filter: {sorted(set(args.years))}")
    else:
        print("Years filter: (all)")
    print(f"Count   : {n}")
    print(f"Min     : {vmin:.3f}")
    print(f"Max     : {vmax:.3f}")
    print(f"Mean    : {mean_val:.3f}")
    print("")

    # Build bins on [0.0, 1.0]
    bins = args.bins
    edges = [i / bins for i in range(bins + 1)]
    counts = [0] * bins

    for v in vals:
        idx = int(v * bins)
        if idx < 0:
            idx = 0
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1

    print("Bin range    | Count | Bar")
    print("-------------+-------+-----------------------")
    max_count = max(counts) or 1
    for i in range(bins):
        lo = edges[i]
        hi = edges[i + 1]
        c = counts[i]
        bar_len = int(20 * c / max_count)
        bar = "#" * bar_len
        print(f"{lo:4.1f}–{hi:4.1f}     | {c:5d} | {bar}")


if __name__ == "__main__":
    main()
