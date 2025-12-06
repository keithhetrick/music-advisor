#!/usr/bin/env python3
import argparse
import csv
import json
import math
from pathlib import Path


def fit_linear(xs, ys):
    """
    Simple least-squares fit: y = a * x + b
    Returns (a, b, r, n).
    """
    n = len(xs)
    if n < 2:
        return float("nan"), float("nan"), float("nan"), n

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))

    if den_x == 0:
        a = 0.0
    else:
        a = num / (den_x ** 2) * den_x  # equivalent to num / sum((x-mean_x)^2)

    # For clarity, compute denominator for slope directly:
    denom = sum((x - mean_x) ** 2 for x in xs) or 1.0
    a = num / denom
    b = mean_y - a * mean_x

    # Pearson r
    r = num / (den_x * den_y) if den_x and den_y else float("nan")

    return a, b, r, n


def main():
    parser = argparse.ArgumentParser(
        description="Fit a simple linear calibration HCI_v1_score -> EchoTarget_v2."
    )
    parser.add_argument(
        "--compare-csv",
        required=True,
        help="CSV produced by hci_compare_targets.py",
    )
    parser.add_argument(
        "--out-json",
        default="calibration/hci_v1_to_EchoTarget_v2_v1.json",
        help="Output JSON file for calibration mapping (default: calibration/hci_v1_to_EchoTarget_v2_v1.json)",
    )
    parser.add_argument(
        "--min-songs",
        type=int,
        default=20,
        help="Minimum number of matched songs required to fit (default: 20)",
    )
    args = parser.parse_args()

    compare_csv = Path(args.compare_csv)
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    xs = []  # HCI_v1_score
    ys = []  # EchoTarget_v2

    with compare_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("match_status") != "matched":
                continue
            try:
                hci = float(row.get("HCI_v1_score", ""))
                et = float(row.get("meta_EchoTarget_v2", ""))
            except Exception:
                continue
            xs.append(hci)
            ys.append(et)

    if len(xs) < args.min_songs:
        print(f"[ERROR] Not enough matched songs with numeric labels (found {len(xs)}, need {args.min_songs}).")
        return

    a, b, r, n = fit_linear(xs, ys)

    calib = {
        "mapping": "EchoTarget_v2 ≈ a * HCI_v1_score + b",
        "a": a,
        "b": b,
        "pearson_r": r,
        "n_songs": n,
        "source_compare_csv": str(compare_csv),
    }

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(calib, f, indent=2)

    print("[OK] Fitted linear calibration:")
    print(f"  ET ≈ {a:.4f} * HCI_v1 + {b:.4f}")
    print(f"  Pearson r = {r:.4f} (n={n})")
    print(f"[OK] Wrote calibration JSON to {out_json}")


if __name__ == "__main__":
    main()
