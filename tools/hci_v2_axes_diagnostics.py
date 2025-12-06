#!/usr/bin/env python3
"""
hci_v2_axes_diagnostics.py

Quick stats + correlations for the 6 audio axes vs:
  - EchoTarget_v2 (label)
  - HCI_audio_v2_hat (prediction)

Operates on the eval CSV produced by hci_v2_eval_training.py, e.g.:
  data/private/local_assets/hci_v2/hci_v2_training_eval_pop_us_2025Q4.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from shared.config.paths import get_hci_v2_training_eval_csv

AXES_CANONICAL = [
    "TempoFit",
    "RuntimeFit",
    "LoudnessFit",
    "Energy",
    "Danceability",
    "Valence",
]

# Some pipelines may use lower_snake_case column names;
# we accept either and resolve per-axis.
AXES_ALIASES = {
    "TempoFit": ["TempoFit", "tempo_fit"],
    "RuntimeFit": ["RuntimeFit", "runtime_fit"],
    "LoudnessFit": ["LoudnessFit", "loudness_fit"],
    "Energy": ["Energy", "energy"],
    "Danceability": ["Danceability", "danceability"],
    "Valence": ["Valence", "valence"],
}

LABEL_COL = "EchoTarget_v2"
PRED_COL = "HCI_audio_v2_hat"


def _pick_col(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in fieldnames:
            return c
    return None


def load_eval_csv(path: Path) -> Tuple[List[Dict[str, float]], Dict[str, str]]:
    rows_num: List[Dict[str, float]] = []
    col_map: Dict[str, str] = {}

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Resolve axis columns
        for axis in AXES_CANONICAL:
            col = _pick_col(fieldnames, AXES_ALIASES[axis])
            if col:
                col_map[axis] = col

        if LABEL_COL in fieldnames:
            col_map[LABEL_COL] = LABEL_COL
        if PRED_COL in fieldnames:
            col_map[PRED_COL] = PRED_COL

        for row in reader:
            out_row: Dict[str, float] = {}
            # Numeric conversion with best-effort
            for key, col in col_map.items():
                val = row.get(col)
                if val in (None, "", "NaN"):
                    continue
                try:
                    out_row[key] = float(val)
                except ValueError:
                    continue
            if out_row:
                rows_num.append(out_row)

    return rows_num, col_map


def summarize(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


def corr(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
    )
    if den <= 0:
        return None
    return num / den


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Diagnostics for HCI_v2 axes vs EchoTarget_v2 and HCI_audio_v2_hat."
    )
    ap.add_argument(
        "--eval-csv",
        default=str(get_hci_v2_training_eval_csv()),
        help=f"Eval CSV path (default: {get_hci_v2_training_eval_csv()})",
    )
    args = ap.parse_args()

    path = Path(args.eval_csv)
    if not path.exists():
        raise SystemExit(f"Eval CSV not found: {path}")

    rows, col_map = load_eval_csv(path)
    if not rows:
        raise SystemExit("No numeric rows found in eval CSV.")

    print(f"[INFO] Loaded {len(rows)} rows from {path}")
    print(f"[INFO] Column mapping: {col_map}")

    # Collect per-axis series
    axis_vals: Dict[str, List[float]] = {a: [] for a in AXES_CANONICAL}
    labels: List[float] = []
    preds: List[float] = []

    for row in rows:
        for axis in AXES_CANONICAL:
            v = row.get(axis)
            if v is not None:
                axis_vals[axis].append(v)
        if LABEL_COL in row:
            labels.append(row[LABEL_COL])
        if PRED_COL in row:
            preds.append(row[PRED_COL])

    print("\nAxis stats:")
    for axis in AXES_CANONICAL:
        vals = axis_vals[axis]
        s = summarize(vals)
        if not s:
            continue
        print(
            f"  {axis:12s} n={s['n']:3d} "
            f"min={s['min']:.3f} max={s['max']:.3f} "
            f"mean={s['mean']:.3f} std={s['std']:.3f}"
        )

    if labels:
        print("\nCorrelations vs EchoTarget_v2:")
        for axis in AXES_CANONICAL:
            xs = axis_vals[axis]
            if len(xs) != len(labels):
                continue
            r = corr(xs, labels)
            if r is not None:
                print(f"  {axis:12s} vs {LABEL_COL:14s}: r={r:.3f}")

    if preds:
        print("\nCorrelations vs HCI_audio_v2_hat:")
        for axis in AXES_CANONICAL:
            xs = axis_vals[axis]
            if len(xs) != len(preds):
                continue
            r = corr(xs, preds)
            if r is not None:
                print(f"  {axis:12s} vs {PRED_COL:14s}: r={r:.3f}")


if __name__ == "__main__":
    main()
