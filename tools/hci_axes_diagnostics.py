#!/usr/bin/env python3
# tools/hci_axes_diagnostics.py
"""
Quick stats + correlations for the 6 canonical audio axes.

Can operate on:
  - One or more features_output roots (scans *.hci.json), and/or
  - A Historical Echo corpus CSV (e.g. data/historical_echo_corpus_2025Q4.csv).

This does NOT modify any files. It's purely a reporting / QA tool.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import itertools
from pathlib import Path
from typing import Dict, List, Tuple

from ma_config.audio import resolve_hci_v2_corpus, resolve_market_norms

AXES = ["TempoFit", "RuntimeFit", "Energy", "Danceability", "Valence", "LoudnessFit"]


# ----------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------

def load_axes_from_hci_root(root: Path) -> Dict[str, List[float]]:
    """
    Scan a features_output root for *.hci.json and extract the 6 audio axes.

    Supports both:
      - "audio_axes": [t, r, e, d, v, l]
      - "axes": {"TempoFit": ..., ...}
    """
    data: Dict[str, List[float]] = {a: [] for a in AXES}

    for hci_path in root.rglob("*.hci.json"):
        try:
            blob = json.loads(hci_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        axes_list = None
        audio_axes = blob.get("audio_axes")
        axes_dict = blob.get("axes")

        if isinstance(audio_axes, list) and len(audio_axes) == 6:
            axes_list = audio_axes
        elif isinstance(axes_dict, dict):
            axes_list = [axes_dict.get(a) for a in AXES]

        if not axes_list:
            continue

        for name, val in zip(AXES, axes_list):
            if val is None:
                continue
            try:
                data[name].append(float(val))
            except (TypeError, ValueError):
                continue

    return data


def load_axes_from_corpus_csv(path: Path) -> Dict[str, List[float]]:
    """
    Load axes from a Historical Echo corpus CSV, assuming column names:
      tempo_fit, runtime_fit, energy, danceability, valence, loudness_fit
    """
    data: Dict[str, List[float]] = {a: [] for a in AXES}

    colmap = {
        "tempo_fit": "TempoFit",
        "runtime_fit": "RuntimeFit",
        "energy": "Energy",
        "danceability": "Danceability",
        "valence": "Valence",
        "loudness_fit": "LoudnessFit",
    }

    corpus_path = resolve_hci_v2_corpus(str(path))
    with corpus_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for csv_name, axis_name in colmap.items():
                v = row.get(csv_name)
                if v in (None, "", "NaN"):
                    continue
                try:
                    data[axis_name].append(float(v))
                except ValueError:
                    continue

    return data


# ----------------------------------------------------------------------
# Stats + correlations
# ----------------------------------------------------------------------

def summarize_axes(data: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    stats: Dict[str, Dict[str, float]] = {}
    for name, vals in data.items():
        if not vals:
            continue
        stats[name] = {
            "n": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": statistics.fmean(vals),
            "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
        }
    return stats


def compute_correlations(data: Dict[str, List[float]]) -> Dict[Tuple[str, str], float]:
    corrs: Dict[Tuple[str, str], float] = {}
    for a, b in itertools.combinations(AXES, 2):
        xs = data.get(a, [])
        ys = data.get(b, [])
        if len(xs) < 2 or len(xs) != len(ys):
            continue

        mx = statistics.fmean(xs)
        my = statistics.fmean(ys)

        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = math.sqrt(
            sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
        )
        if den <= 0:
            continue

        corrs[(a, b)] = num / den

    return corrs


def print_report(label: str, data: Dict[str, List[float]]) -> None:
    stats = summarize_axes(data)
    corrs = compute_correlations(data)

    print(f"\n=== {label} ===")
    print("Axis stats:")
    for name in AXES:
        if name not in stats:
            continue
        s = stats[name]
        print(
            f"  {name:12s} n={s['n']:3d} "
            f"min={s['min']:.3f} max={s['max']:.3f} "
            f"mean={s['mean']:.3f} std={s['std']:.3f}"
        )

    print("\nPairwise correlations (r):")
    if not corrs:
        print("  <not enough data>")
        return

    for (a, b), r in sorted(corrs.items(), key=lambda kv: -abs(kv[1])):
        print(f"  {a:12s} vs {b:12s}: r={r:.3f}")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Diagnostics for HCI audio axes (stats + correlations)."
    )
    ap.add_argument(
        "--root",
        action="append",
        help="features_output root (e.g. features_output/2025/11/17). "
             "Can be passed multiple times.",
    )
    ap.add_argument(
        "--corpus",
        type=str,
        help="Optional Historical Echo corpus CSV "
             "(e.g. data/historical_echo_corpus_2025Q4.csv).",
    )
    args = ap.parse_args()

    if not args.root and not args.corpus:
        ap.error("Specify at least one --root and/or --corpus")

    # Per-root reports
    if args.root:
        for r in args.root:
            root = Path(r)
            data = load_axes_from_hci_root(root)
            print_report(f"hci root: {root}", data)

    # Corpus report
    if args.corpus:
        corpus_path = Path(args.corpus)
        corpus_data = load_axes_from_corpus_csv(corpus_path)
        print_report(f"corpus: {corpus_path}", corpus_data)


if __name__ == "__main__":
    main()
