#!/usr/bin/env python3
# tools/calibration_runner.py
# Build a monotonic calibration from your existing *.pack.json files.

from __future__ import annotations
import argparse, json, os, re, glob
from typing import List, Tuple, Dict
from hci_calibrator import fit_isotonic, summarize, ks_stat, save_calibration

# Folder→target mapping (tune as you like, monotone mapping learns shape)
FOLDER_TARGETS = {
    # high structural fit anchors
    "00_core_modern": 0.85,
    "01_echo_1985_89": 0.75,
    "02_echo_1990_94": 0.75,
    "03_echo_1995_99": 0.70,
    "04_echo_2000_04": 0.70,
    "05_echo_2005_09": 0.70,
    "06_echo_2010_14": 0.75,
    "07_echo_2015_19": 0.75,
    # genre nuance / neutral anchors
    "08_indie_singer_songwriter": 0.50,
    "09_latin_crossover_eval": 0.65,
    # negatives
    "10_negatives_main_eval": 0.15,
    "11_negatives_canonical_eval": 0.15,
    "12_negatives_novelty_eval": 0.10,
    # legacy/evolution: neutral-ish
    "99_legacy_pop_eval": 0.50,
}

PACK_GLOB = "**/*.pack.json"

def infer_folder_label(root: str, pack_path: str) -> Tuple[str, float] | None:
    # Returns (anchor_folder, target) or None
    rel = os.path.relpath(pack_path, root)
    first = rel.split(os.sep)[0]
    if first in FOLDER_TARGETS:
        return first, FOLDER_TARGETS[first]
    return None

def load_hci_from_pack(pack_path: str) -> float | None:
    try:
        with open(pack_path, "r") as f:
            d = json.load(f)
        return float(((d.get("HCI_v1") or {}).get("HCI_v1_score")))
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser(description="Learn HCI calibration from packs.")
    ap.add_argument("--calib-root", required=True, help="Root folder containing anchor subfolders and generated *.pack.json files.")
    ap.add_argument("--region", default="US")
    ap.add_argument("--profile", default="Pop")
    ap.add_argument("--out-json", required=True, help="Output calibration json (e.g., /path/to/hci_calibration_pop_us_2025Q4.json)")
    ap.add_argument("--ref-calibration", help="Optional previous calibration json for drift comparison.")
    ap.add_argument("--notes", help="Optional notes to store in calibration file.")
    args = ap.parse_args()

    pack_paths = [p for p in glob.glob(os.path.join(args.calib_root, PACK_GLOB), recursive=True) if p.endswith(".pack.json")]
    raw_scores: List[float] = []
    targets: List[float] = []
    weights: List[float] = []

    for p in pack_paths:
        lbl = infer_folder_label(args.calib_root, p)
        if not lbl:
            continue
        _, tgt = lbl
        hci = load_hci_from_pack(p)
        if hci is None:
            continue
        # keep only valid [0,1]
        if not (0.0 <= hci <= 1.0):
            continue
        raw_scores.append(hci)
        targets.append(tgt)
        weights.append(1.0)

    if not raw_scores:
        raise SystemExit("No pack files found (or none with valid HCI_v1).")

    # Fit monotonic mapping
    from hci_calibrator import Knot
    knots: List[Knot] = fit_isotonic(raw_scores, targets, weights)

    # Drift comparison (optional)
    ref_summary = None
    ks = None
    if args.ref_calibration and os.path.exists(args.ref_calibration):
        with open(args.ref_calibration, "r") as f:
            ref = json.load(f)
        ref_summary = ref.get("raw_summary")
        # We compare *distributions of raw HCI*; if you stored historic raw HCI,
        # you can pass it in separately. Here we compare summaries via KS with a proxy:
        # fall back to comparing raw summaries if needed.
        # (If you want a true distribution KS vs. reference, store the raw list.)
        ks = None

    raw_summary = summarize(raw_scores)
    save_calibration(
        path=args.out_json,
        region=args.region,
        profile=args.profile,
        knots=knots,
        raw_summary=raw_summary,
        ref_summary=ref_summary,
        ks=ks,
        source_path=os.path.abspath(args.calib_root),
        notes=args.notes or "Auto-generated via calibration_runner.py"
    )
    print(f"[calibration] Wrote {args.out_json} with {raw_summary['n']} samples and {len(knots)} knots.")

if __name__ == "__main__":
    main()
