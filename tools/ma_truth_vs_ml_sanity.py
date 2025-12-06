#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BANDS = ("lo", "mid", "hi")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sanity check: truth vs ML vs feature bands for "
                    "energy and danceability."
    )
    p.add_argument(
        "--csv",
        required=True,
        help="Joined CSV (e.g. calibration/aee_ml_reports/truth_vs_ml_v1_1.csv)",
    )
    p.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Max rows to show in each mismatch list (default: 25)",
    )
    p.add_argument(
        "--thresholds",
        help="Optional JSON thresholds file "
             "(e.g. calibration/aee_band_thresholds_v1_1.json). "
             "If omitted or missing, thresholds are computed from data "
             "via 0.30 / 0.70 quantiles.",
    )
    return p.parse_args()


def quantile(values: List[float], q: float) -> float:
    if not values:
        raise ValueError("quantile() called with empty list")
    xs = sorted(values)
    n = len(xs)
    if n == 1:
        return xs[0]
    q = max(0.0, min(1.0, q))
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] + (xs[hi] - xs[lo]) * frac


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def compute_feature_thresholds_from_rows(
    rows: List[Dict[str, str]],
    col: str,
    p_lo: float = 0.30,
    p_hi: float = 0.70,
) -> Optional[Tuple[float, float, int]]:
    vals: List[float] = []
    for row in rows:
        raw = (row.get(col) or "").strip()
        if not raw:
            continue
        try:
            vals.append(float(raw))
        except ValueError:
            continue
    if not vals:
        return None
    lo_th = quantile(vals, p_lo)
    hi_th = quantile(vals, p_hi)
    return lo_th, hi_th, len(vals)


def load_thresholds(
    args: argparse.Namespace, rows: List[Dict[str, str]]
) -> Dict[str, Dict[str, float]]:
    """
    Returns:
      {
        "energy_feature": {"lo": float, "hi": float, "source": "..."},
        "danceability_feature": {"lo": float, "hi": float, "source": "..."},
      }
    """
    thresholds: Dict[str, Dict[str, float]] = {}
    cfg = None
    cfg_path: Optional[Path] = None

    if args.thresholds:
        cfg_path = Path(args.thresholds)
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[WARN] Failed to load thresholds JSON: {e}")
                cfg = None
        else:
            print(f"[WARN] Thresholds file not found: {cfg_path}")

    for key in ("energy_feature", "danceability_feature"):
        if cfg and key in cfg:
            info = cfg[key]
            try:
                lo_th = float(info["threshold_lo"])
                hi_th = float(info["threshold_hi"])
                src = cfg_path.name if cfg_path is not None else "thresholds_json"
                thresholds[key] = {"lo": lo_th, "hi": hi_th, "source": src}
                continue
            except Exception as e:
                print(f"[WARN] Bad thresholds for {key} in JSON: {e}")

        # Fall back to quantiles from CSV
        q_res = compute_feature_thresholds_from_rows(rows, key)
        if q_res is None:
            print(f"[WARN] Could not compute thresholds for {key} from data")
            continue
        lo_th, hi_th, n_vals = q_res
        thresholds[key] = {
            "lo": lo_th,
            "hi": hi_th,
            "source": f"csv_quantiles(n={n_vals})",
        }

    return thresholds


def band_from_feature(val: float, lo_th: float, hi_th: float) -> str:
    if val < lo_th:
        return "lo"
    if val > hi_th:
        return "hi"
    return "mid"


def print_axis_summary(
    axis_name: str,
    confusion: Dict[str, Dict[str, int]],
    n_total: int,
    n_correct: int,
) -> None:
    print(f"=== {axis_name.upper()} axis ===")
    print(f"n_total   = {n_total}")
    print(f"n_correct = {n_correct}")
    acc = (n_correct / n_total) if n_total else 0.0
    print(f"accuracy  = {acc:.3f}\n")

    print("Confusion matrix (truth rows, predicted cols):")
    print("truth \\ pred\t" + "\t".join(BANDS))
    for t in BANDS:
        row_vals = "\t".join(str(confusion[t][p]) for p in BANDS)
        print(f"{t}\t{row_vals}")
    print()


def print_band_stats(
    axis_name: str,
    label: str,
    counts: Dict[str, int],
    denom: int,
) -> None:
    axis_label = axis_name.capitalize()
    total = sum(counts.values())
    # Use denom if provided, else fallback to total so percentages look sane
    denom = denom or total or 1
    print(f"{axis_label} {label} bands:")
    for b in BANDS:
        c = counts.get(b, 0)
        pct = 100.0 * c / denom
        print(f"  {b}: {c} ({pct:.2f}%)")
    print()


def print_mismatches(
    axis_name: str,
    label: str,
    items: List[Tuple[str, str, str, Optional[float], Optional[str]]],
    top_n: int,
) -> None:
    print(f"=== {axis_name.upper()}: {label} (showing up to {top_n}) ===")
    if not items:
        print("  (none)\n")
        return

    for idx, (identity, truth, ml, feat_val, feat_band) in enumerate(
        items[:top_n], start=1
    ):
        print(f" {idx}. {identity}")
        if feat_val is None or feat_band is None:
            print(f"    truth={truth}, ml={ml}, feat=NA, feat_band=NA")
        else:
            print(
                f"    truth={truth}, ml={ml}, "
                f"feat={feat_val}, feat_band={feat_band}"
            )
    print()


def analyze_axis(
    axis_name: str,
    rows: List[Dict[str, str]],
    truth_col: str,
    ml_col: str,
    feature_col: str,
    thresholds: Dict[str, Dict[str, float]],
    top_n: int,
) -> None:
    confusion: Dict[str, Dict[str, int]] = {
        t: {p: 0 for p in BANDS} for t in BANDS
    }
    truth_counts = {b: 0 for b in BANDS}
    ml_counts = {b: 0 for b in BANDS}
    feat_counts = {b: 0 for b in BANDS}

    n_total = 0
    n_correct = 0

    mism_truth_vs_ml: List[Tuple[str, str, str, Optional[float], Optional[str]]] = []
    mism_truth_vs_feat: List[Tuple[str, str, str, Optional[float], Optional[str]]] = []
    mism_ml_vs_feat: List[Tuple[str, str, str, Optional[float], Optional[str]]] = []

    th = thresholds.get(feature_col)
    lo_th = hi_th = None
    if th:
        lo_th = th["lo"]
        hi_th = th["hi"]

    for row in rows:
        truth = (row.get(truth_col) or "").strip().lower()
        ml = (row.get(ml_col) or "").strip().lower()
        feat_raw = (row.get(feature_col) or "").strip()

        feat_val: Optional[float] = None
        feat_band: Optional[str] = None

        if feat_raw:
            try:
                feat_val = float(feat_raw)
            except ValueError:
                feat_val = None

        if feat_val is not None and lo_th is not None and hi_th is not None:
            feat_band = band_from_feature(feat_val, lo_th, hi_th)

        # Confusion + basic counts
        if truth in BANDS and ml in BANDS:
            n_total += 1
            confusion[truth][ml] += 1
            truth_counts[truth] += 1
            ml_counts[ml] += 1
            if truth == ml:
                n_correct += 1

        # Feature band counts
        if feat_band in BANDS:
            feat_counts[feat_band] += 1

        # Build identity string
        identity = (
            f"{(row.get('audio_name') or '').strip()} | "
            f"{(row.get('artist') or '').strip()} – "
            f"{(row.get('title') or '').strip()}"
        )

        # If we don't have a feature band, we can still log truth != ML mismatches
        if feat_band not in BANDS or feat_val is None:
            if truth in BANDS and ml in BANDS and truth != ml:
                mism_truth_vs_ml.append((identity, truth, ml, None, None))
            continue

        # Mismatch buckets
        if truth in BANDS and ml in BANDS:
            if truth != ml:
                mism_truth_vs_ml.append((identity, truth, ml, feat_val, feat_band))
            if truth != feat_band:
                mism_truth_vs_feat.append((identity, truth, ml, feat_val, feat_band))
            if ml != feat_band:
                mism_ml_vs_feat.append((identity, truth, ml, feat_val, feat_band))

    print_axis_summary(axis_name, confusion, n_total, n_correct)
    print_band_stats(axis_name, "truth", truth_counts, n_total)
    print_band_stats(axis_name, "ML", ml_counts, n_total)
    print_band_stats(axis_name, "feature-derived", feat_counts, n_total)

    print_mismatches(axis_name, "truth != ML", mism_truth_vs_ml, top_n)
    print_mismatches(axis_name, "truth != feature_band", mism_truth_vs_feat, top_n)
    print_mismatches(axis_name, "ML != feature_band", mism_ml_vs_feat, top_n)


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"[ERROR] CSV not found: {csv_path}")

    rows = load_rows(csv_path)
    thresholds = load_thresholds(args, rows)

    # Announce thresholds being used
    for key, label in (
        ("energy_feature", "ENERGY"),
        ("danceability_feature", "DANCE"),
    ):
        info = thresholds.get(key)
        if not info:
            print(f"[WARN] No thresholds for {key}; "
                  f"feature bands for {label} will be skipped.")
        else:
            print(
                f"[INFO] {label} feature thresholds: "
                f"lo<{info['lo']:.6f}, hi>{info['hi']:.6f} "
                f"(source={info['source']})"
            )
    print()

    analyze_axis(
        "energy",
        rows,
        truth_col="energy_truth",
        ml_col="energy_ml",
        feature_col="energy_feature",
        thresholds=thresholds,
        top_n=args.top_n,
    )

    analyze_axis(
        "dance",
        rows,
        truth_col="dance_truth",
        ml_col="dance_ml",
        feature_col="danceability_feature",
        thresholds=thresholds,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
