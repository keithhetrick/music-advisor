#!/usr/bin/env python3
# tools/ma_fit_hci_calibration_from_hitlist.py
"""
Fit HCI calibration (scale + offset) for a given anchor using the 2025 Hit List.

Pipeline:
- You provide a CSV with columns: audio_name,target_hci
- For each audio_name, we look for <audio_name>.hci.json somewhere under data/features_output/
- From each .hci.json we read HCI_v1.raw
- We then solve a least-squares linear fit: target ≈ scale * raw + offset
- We update calibration/hci_calibration_pop_us_2025Q4.json:
    anchors[anchor_name] = {
        "scale": <scale>,
        "offset": <offset>,
        "raw_mean": <mean(raw_i)>,
        "target_mean": <mean(target_i)>
    }

Usage example:

  python tools/ma_fit_hci_calibration_from_hitlist.py \\
    --hitlist shared/calibration/hitlist_pop_us_2025_core_v1_1.csv \\
    --anchor 00_core_modern

This will modify shared/calibration/hci_calibration_pop_us_2025Q4.json in-place,
backing up the original file as *.bak.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any


@dataclass
class Pair:
    audio_name: str
    raw: float
    target: float


def load_hitlist_csv(path: Path) -> List[Tuple[str, float]]:
    rows: List[Tuple[str, float]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "audio_name" not in reader.fieldnames or "target_hci" not in reader.fieldnames:
            raise ValueError(
                f"{path} must have columns: audio_name,target_hci (got {reader.fieldnames})"
            )
        for row in reader:
            name = row["audio_name"].strip()
            if not name:
                continue
            try:
                target = float(row["target_hci"])
            except (TypeError, ValueError):
                continue
            rows.append((name, target))
    return rows


def scan_hci_files(hci_root: Path) -> Dict[str, float]:
    """
    Scan for *.hci.json and return mapping:
      audio_name (stem) -> HCI_v1.raw
    """
    out: Dict[str, float] = {}
    for p in hci_root.rglob("*.hci.json"):
        stem = p.stem  # e.g. 2020_the_weeknd__blinding_lights__album
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        hci = data.get("HCI_v1", {})
        raw = hci.get("raw")
        if not isinstance(raw, (int, float)):
            continue
        out[stem] = float(raw)
    return out


def make_pairs(
    hitlist: List[Tuple[str, float]],
    raw_map: Dict[str, float],
) -> List[Pair]:
    pairs: List[Pair] = []
    missing: List[str] = []
    for audio_name, target in hitlist:
        if audio_name not in raw_map:
            missing.append(audio_name)
            continue
        pairs.append(Pair(audio_name=audio_name, raw=raw_map[audio_name], target=target))

    if missing:
        print("WARNING: No raw HCI found for these audio_name entries:")
        for name in missing:
            print(f"  - {name}")
        print("They will be ignored in the fit.\n")

    if not pairs:
        raise RuntimeError("No matching audio_name entries had raw HCI values. Nothing to fit.")

    return pairs


def fit_scale_offset(pairs: List[Pair]) -> Tuple[float, float]:
    """
    Least-squares fit for:
        target ≈ scale * raw + offset
    Returns (scale, offset).
    """
    n = len(pairs)
    if n < 2:
        # Not enough points to fit a line; fall back to identity
        return 1.0, 0.0

    sum_raw = sum(p.raw for p in pairs)
    sum_target = sum(p.target for p in pairs)
    sum_raw2 = sum(p.raw * p.raw for p in pairs)
    sum_raw_target = sum(p.raw * p.target for p in pairs)

    denom = n * sum_raw2 - sum_raw * sum_raw
    if abs(denom) < 1e-8:
        # Degenerate case; all raws equal or something pathological
        return 1.0, 0.0

    scale = (n * sum_raw_target - sum_raw * sum_target) / denom
    offset = (sum_target - scale * sum_raw) / n
    return scale, offset


def compute_means(pairs: List[Pair]) -> Tuple[float, float]:
    n = len(pairs)
    mean_raw = sum(p.raw for p in pairs) / n
    mean_target = sum(p.target for p in pairs) / n
    return mean_raw, mean_target


def compute_rmse(pairs: List[Pair], scale: float, offset: float) -> float:
    if not pairs:
        return 0.0
    sq = 0.0
    for p in pairs:
        pred = scale * p.raw + offset
        err = pred - p.target
        sq += err * err
    return math.sqrt(sq / len(pairs))


def update_calibration(
    calib_path: Path,
    anchor_name: str,
    scale: float,
    offset: float,
    mean_raw: float,
    mean_target: float,
) -> None:
    """
    Update calibration JSON in-place:
      calibration/hci_calibration_pop_us_2025Q4.json

    Ensures structure:

      {
        "cap_min": 0.0,
        "cap_max": 1.0,
        "anchors": {
          "<anchor_name>": {
            "scale": <scale>,
            "offset": <offset>,
            "raw_mean": <mean_raw>,
            "target_mean": <mean_target>
          },
          ...
        }
      }
    """
    if not calib_path.exists():
        raise FileNotFoundError(f"Calibration file not found: {calib_path}")

    data = json.loads(calib_path.read_text())

    anchors = data.get("anchors")
    if not isinstance(anchors, dict):
        anchors = {}
        data["anchors"] = anchors

    anchors[anchor_name] = {
        "scale": scale,
        "offset": offset,
        "raw_mean": mean_raw,
        "target_mean": mean_target,
    }

    # Ensure caps exist (you can tweak these if needed)
    if "cap_min" not in data:
        data["cap_min"] = 0.0
    if "cap_max" not in data:
        data["cap_max"] = 1.0

    # Backup original
    backup = calib_path.with_suffix(calib_path.suffix + ".bak")
    backup.write_text(json.dumps(data, indent=2))
    print(f"Backup written to: {backup}")

    # Overwrite main file
    calib_path.write_text(json.dumps(data, indent=2))
    print(f"Updated calibration written to: {calib_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--hitlist",
        required=True,
        help="Path to hitlist CSV with columns: audio_name,target_hci",
    )
    ap.add_argument(
        "--anchor",
        default="00_core_modern",
        help="Calibration anchor to update (default: 00_core_modern)",
    )
    ap.add_argument(
        "--hci-root",
        default="data/features_output",
        help="Root directory containing *.hci.json (default: data/features_output)",
    )
    ap.add_argument(
        "--calibration",
        default="shared/calibration/hci_calibration_pop_us_2025Q4.json",
        help="Path to the calibration JSON to update (default: shared/calibration/hci_calibration_pop_us_2025Q4.json)",
    )
    args = ap.parse_args()

    here = Path(__file__).resolve()
    repo_root = here.parents[1]

    hitlist_path = (repo_root / args.hitlist).resolve()
    hci_root = (repo_root / args.hci_root).resolve()
    calib_path = (repo_root / args.calibration).resolve()

    print(f"Hitlist CSV: {hitlist_path}")
    print(f"HCI root:    {hci_root}")
    print(f"Calibration: {calib_path}")
    print(f"Anchor:      {args.anchor}\n")

    hitlist_rows = load_hitlist_csv(hitlist_path)
    print(f"Loaded {len(hitlist_rows)} hitlist entries.")

    raw_map = scan_hci_files(hci_root)
    print(f"Found {len(raw_map)} tracks with HCI_v1.raw under {hci_root}.\n")

    pairs = make_pairs(hitlist_rows, raw_map)
    print(f"Using {len(pairs)} matched tracks for fit.\n")

    scale, offset = fit_scale_offset(pairs)
    mean_raw, mean_target = compute_means(pairs)
    rmse = compute_rmse(pairs, scale, offset)

    print("Fitted calibration:")
    print(f"  scale       = {scale:.6f}")
    print(f"  offset      = {offset:.6f}")
    print(f"  raw_mean    = {mean_raw:.6f}")
    print(f"  target_mean = {mean_target:.6f}")
    print(f"  RMSE        = {rmse:.6f}\n")

    update_calibration(
        calib_path=calib_path,
        anchor_name=args.anchor,
        scale=scale,
        offset=offset,
        mean_raw=mean_raw,
        mean_target=mean_target,
    )


if __name__ == "__main__":
    main()
