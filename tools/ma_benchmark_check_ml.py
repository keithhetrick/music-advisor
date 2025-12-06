#!/usr/bin/env python3
# tools/ma_benchmark_check_ml.py
"""
Benchmark ML-calibrated Energy & Danceability axes against benchmark_truth.csv.

Strict allowlist behavior:
- Only songs listed in benchmark_truth.csv are eligible for scoring.
- For each canonical audio_name, we use at most ONE ML sidecar (first found).
- Extra runs of the same song are ignored for accuracy (but harmless).
- Songs with ML sidecars but no truth row are reported but not scored.

Usage (from repo root):

    python tools/ma_benchmark_check_ml.py \
        --truth calibration/benchmark_truth.csv \
        --ml-root calibration/aee_ml_outputs \
        --out calibration/aee_ml_reports/benchmark_ml.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

BANDS = ["lo", "mid", "hi"]


@dataclass
class AxisStats:
    axis: str
    n_total: int
    n_correct: int
    accuracy: float
    confusion: Dict[Tuple[str, str], int]  # (truth, pred) -> count


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Benchmark ML-calibrated Energy/Danceability against truth (allowlist)."
    )
    p.add_argument(
        "--truth",
        required=True,
        help="Path to calibration/benchmark_truth.csv",
    )
    p.add_argument(
        "--ml-root",
        required=True,
        help="Directory containing *.ml_axes.json outputs from ma_aee_ml_apply.py",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Optional path to write a text report (e.g. calibration/aee_ml_reports/benchmark_ml.txt)",
    )
    return p.parse_args(argv)


def canonical_audio_name(name: str) -> str:
    """Strip trailing timestamp suffix like '_20251114_070344' if present."""
    name = (name or "").strip()
    if not name:
        return ""
    m = re.search(r"_(\d{8}_\d{6})$", name)
    if m:
        return name[: m.start()]
    return name


def _load_truth(truth_csv: Path) -> Dict[str, Dict[str, str]]:
    """
    Return mapping: canonical audio_name -> {energy_band_truth, dance_band_truth}.
    This is the allowlist for benchmarking.
    """
    out: Dict[str, Dict[str, str]] = {}
    with truth_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audio_name_raw = (row.get("audio_name") or "").strip()
            audio_name = canonical_audio_name(audio_name_raw)
            if not audio_name:
                continue
            energy_band = (row.get("energy_band_truth") or "").strip().lower()
            dance_band = (row.get("dance_band_truth") or "").strip().lower()
            out[audio_name] = {
                "energy": energy_band,
                "dance": dance_band,
            }
    return out


def _iter_ml_sidecars(root: Path) -> List[Path]:
    if root.is_file() and root.suffix == ".json":
        return [root]
    return sorted(root.rglob("*.ml_axes.json"))


def _load_ml_axes(path: Path) -> Dict[str, str]:
    """Return both raw and canonical names + bands."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    audio_name_raw = (data.get("audio_name") or "").strip()
    audio_name = canonical_audio_name(audio_name_raw)

    axes_ml = data.get("axes_ml") or {}
    energy_obj = axes_ml.get("Energy") or {}
    dance_obj = axes_ml.get("Danceability") or {}

    energy_band_ml = (energy_obj.get("band") or "").strip().lower()
    dance_band_ml = (dance_obj.get("band") or "").strip().lower()

    return {
        "audio_name": audio_name,           # canonical
        "audio_name_raw": audio_name_raw,   # full, with timestamp if present
        "energy_band_ml": energy_band_ml,
        "dance_band_ml": dance_band_ml,
    }


def _init_confusion() -> Dict[Tuple[str, str], int]:
    conf: Dict[Tuple[str, str], int] = {}
    for t in BANDS:
        for p in BANDS:
            conf[(t, p)] = 0
    return conf


def _group_ml_by_truth(
    truth_map: Dict[str, Dict[str, str]],
    ml_root: Path,
) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    """
    Group ML predictions by canonical audio_name, but only for songs in truth_map.

    Returns:
        groups: audio_name -> one representative ML record (first seen)
        extras: list of raw audio_names that had ML sidecars but no truth row
    """
    groups: Dict[str, Dict[str, str]] = {}
    extras: List[str] = []

    for sidecar in _iter_ml_sidecars(ml_root):
        ml = _load_ml_axes(sidecar)
        audio_name = ml["audio_name"]
        audio_name_raw = ml["audio_name_raw"] or audio_name
        if not audio_name:
            continue

        if audio_name not in truth_map:
            # Not in allowlist; record as extra/unlabeled
            extras.append(audio_name_raw)
            continue

        # Allowlist hit: keep the first sidecar we see for this song
        if audio_name in groups:
            continue
        groups[audio_name] = ml

    return groups, sorted(set(extras))


def compute_axis_stats(
    truth_map: Dict[str, Dict[str, str]],
    ml_root: Path,
) -> Tuple[AxisStats, AxisStats, List[str], List[str]]:
    """
    Compute stats for Energy and Danceability.

    Only one ML sample per truth-row song is used (first matching sidecar).
    Returns:
        energy_stats, dance_stats,
        extras_with_ml_but_no_truth,
        truth_songs_missing_ml
    """
    energy_conf = _init_confusion()
    dance_conf = _init_confusion()

    energy_n_total = 0
    energy_n_correct = 0
    dance_n_total = 0
    dance_n_correct = 0

    groups, extras = _group_ml_by_truth(truth_map, ml_root)

    # Truth songs that have NO ML sidecar
    truth_missing_ml = [name for name in truth_map.keys() if name not in groups]

    # Score only songs that are in both truth_map and groups (1:1)
    for audio_name, ml in groups.items():
        truth = truth_map[audio_name]

        truth_energy = truth.get("energy", "")
        truth_dance = truth.get("dance", "")

        ml_energy = ml["energy_band_ml"]
        ml_dance = ml["dance_band_ml"]

        # Energy
        if truth_energy in BANDS and ml_energy in BANDS:
            energy_n_total += 1
            if ml_energy == truth_energy:
                energy_n_correct += 1
            energy_conf[(truth_energy, ml_energy)] += 1

        # Danceability
        if truth_dance in BANDS and ml_dance in BANDS:
            dance_n_total += 1
            if ml_dance == truth_dance:
                dance_n_correct += 1
            dance_conf[(truth_dance, ml_dance)] += 1

    energy_acc = float(energy_n_correct) / energy_n_total if energy_n_total else 0.0
    dance_acc = float(dance_n_correct) / dance_n_total if dance_n_total else 0.0

    energy_stats = AxisStats(
        axis="Energy",
        n_total=energy_n_total,
        n_correct=energy_n_correct,
        accuracy=energy_acc,
        confusion=energy_conf,
    )
    dance_stats = AxisStats(
        axis="Danceability",
        n_total=dance_n_total,
        n_correct=dance_n_correct,
        accuracy=dance_acc,
        confusion=dance_conf,
    )
    return energy_stats, dance_stats, extras, truth_missing_ml


def _format_confusion(axis_stats: AxisStats) -> str:
    lines: List[str] = []
    lines.append(f"Confusion matrix for {axis_stats.axis} (truth rows, predicted cols):")
    header = ["truth \\ pred"] + [b for b in BANDS]
    lines.append("  " + "\t".join(header))
    for t in BANDS:
        row_vals = [t]
        for p in BANDS:
            row_vals.append(str(axis_stats.confusion[(t, p)]))
        lines.append("  " + "\t".join(row_vals))
    return "\n".join(lines)


def _stats_to_text(
    energy_stats: AxisStats,
    dance_stats: AxisStats,
    extras: List[str],
    truth_missing_ml: List[str],
    n_truth_rows: int,
) -> str:
    lines: List[str] = []
    lines.append("=== ML Benchmark vs benchmark_truth.csv (1:1 allowlist) ===")
    lines.append("")
    lines.append(f"Truth rows in CSV (allowlist): {n_truth_rows}")
    lines.append(f"Truth rows with ML sidecars:   {energy_stats.n_total}")
    lines.append(f"Truth rows missing ML:         {len(truth_missing_ml)}")
    lines.append("")

    lines.append("Energy axis:")
    lines.append(
        f"  n_total   = {energy_stats.n_total}"
        f"\n  n_correct = {energy_stats.n_correct}"
        f"\n  accuracy  = {energy_stats.accuracy:.3f}"
    )
    lines.append("")
    lines.append(_format_confusion(energy_stats))
    lines.append("")

    lines.append("Danceability axis:")
    lines.append(
        f"  n_total   = {dance_stats.n_total}"
        f"\n  n_correct = {dance_stats.n_correct}"
        f"\n  accuracy  = {dance_stats.accuracy:.3f}"
    )
    lines.append("")
    lines.append(_format_confusion(dance_stats))
    lines.append("")

    if truth_missing_ml:
        lines.append("Truth songs with NO ML sidecar (not scored):")
        for name in truth_missing_ml:
            lines.append(f"  - {name}")
        lines.append("")
    else:
        lines.append("All truth songs had at least one ML sidecar.")
        lines.append("")

    if extras:
        lines.append("Tracks with ML sidecars but no matching truth row (unlabeled, not scored):")
        for name in extras:
            lines.append(f"  - {name}")
        lines.append("")
    else:
        lines.append("No extra ML sidecars outside the truth allowlist.")
        lines.append("")

    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    truth_csv = Path(args.truth).expanduser().resolve()
    ml_root = Path(args.ml_root).expanduser().resolve()

    if not truth_csv.is_file():
        print(f"[ma_benchmark_check_ml] ERROR: truth CSV not found: {truth_csv}")
        return 1
    if not ml_root.exists():
        print(f"[ma_benchmark_check_ml] ERROR: ml-root does not exist: {ml_root}")
        return 1

    truth_map = _load_truth(truth_csv)
    energy_stats, dance_stats, extras, truth_missing_ml = compute_axis_stats(
        truth_map, ml_root
    )
    report_text = _stats_to_text(
        energy_stats,
        dance_stats,
        extras,
        truth_missing_ml,
        n_truth_rows=len(truth_map),
    )

    print(report_text)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_text, encoding="utf-8")
        print(f"[ma_benchmark_check_ml] Wrote report to {out_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
