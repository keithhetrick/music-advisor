#!/usr/bin/env python3
"""
Benchmark checker for MusicAdvisor features vs. benchmark_truth.csv.

This script is intentionally **read-only**:
- It loads the ground truth CSV (tempo feel, runtime band, loudness band, energy/dance/valence bands).
- It walks a directory of *.features.json files (from tools/ma_audio_features.py).
- It compares the numeric features to the truth bands, prints per-song diffs, and
  prints axis-level accuracy.

CLI (unchanged):

    python tools/ma_benchmark_check.py \
        --truth calibration/benchmark_truth.csv \
        --root  features_output \
        --out   calibration/benchmark_diff_report.txt

The output format is stable so existing docs and workflows still apply.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Banding helpers for structural axes (runtime, loudness)
# ---------------------------------------------------------------------------


def band_runtime(duration_sec: float) -> str:
    """
    Map duration in seconds to runtime band.

    Heuristic (kept consistent with earlier versions):
      - short:  < 150s  (~2:30)
      - mid:   150–260s (~2:30–4:20)
      - long:  > 260s   (epic / extended)
    """
    if duration_sec <= 0:
        return "unknown"
    if duration_sec < 150.0:
        return "short"
    if duration_sec <= 260.0:
        return "mid"
    return "long"


def band_loudness(lufs: float) -> str:
    """
    Map integrated LUFS to broad loudness bands.

    Re-aligned to match the original benchmark behavior:
      - lo  : < -18.0 LUFS
      - mid : -18.0 to -11.0 LUFS
      - hi  : > -11.0 LUFS
    """
    if not math.isfinite(lufs):
        return "unknown"

    if lufs < -18.0:
        return "lo"
    if lufs < -11.0:
        return "mid"
    return "hi"


# ---------------------------------------------------------------------------
# Banding for 0-1 axes (energy, danceability, valence)
# ---------------------------------------------------------------------------

# Defaults (approximate, used as fallback if auto-calibration fails)
DEFAULT_THRESHOLDS = (0.33, 0.66)

ENERGY_THRESHOLDS: Tuple[float, float] = DEFAULT_THRESHOLDS
DANCE_THRESHOLDS: Tuple[float, float] = DEFAULT_THRESHOLDS
VALENCE_THRESHOLDS: Tuple[float, float] = DEFAULT_THRESHOLDS


def band_from_thresholds(
    value: Optional[float],
    thresholds: Tuple[float, float],
) -> str:
    """
    Generic helper: map 0-1 value to {lo, mid, hi} using supplied thresholds.
    """
    if value is None or not math.isfinite(value):
        return "unknown"

    v = float(value)
    lo_t, hi_t = thresholds
    if v < lo_t:
        return "lo"
    if v < hi_t:
        return "mid"
    return "hi"


def band_energy(value: Optional[float]) -> str:
    return band_from_thresholds(value, ENERGY_THRESHOLDS)


def band_dance(value: Optional[float]) -> str:
    return band_from_thresholds(value, DANCE_THRESHOLDS)


def band_valence(value: Optional[float]) -> str:
    return band_from_thresholds(value, VALENCE_THRESHOLDS)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_features_json(root: Path, audio_name: str) -> Optional[Path]:
    """
    Look for a *.features.json that corresponds to this audio_name.

    Convention in this repo is usually:
        features_output/<audio_name>.features.json

    But to be a bit more forgiving we also allow:
        - Any *.features.json whose filename *starts with* the audio_name
        - Any *.features.json whose filename contains the audio_name as a substring
    """
    candidates: List[Path] = []

    if root.is_file() and root.suffix == ".json":
        # Direct file passed as --root
        candidates = [root]
    else:
        for p in root.rglob("*.features.json"):
            name = p.stem  # stem without suffix
            if name.startswith(audio_name):
                candidates.append(p)

        if not candidates:
            for p in root.rglob("*.features.json"):
                if audio_name in p.name:
                    candidates.append(p)

    if not candidates:
        return None
    if len(candidates) > 1:
        # Prefer the one whose stem matches exactly if present
        for c in candidates:
            if c.stem == audio_name:
                return c
    return candidates[0]


# ---------------------------------------------------------------------------
# Axis comparison
# ---------------------------------------------------------------------------


def compare_one(
    truth_row: Dict[str, str],
    feats: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare a single song's features to the benchmark truth row.

    Returns a dict with:
      - audio_name, artist, title
      - per-axis local/truth/bands/status
    """
    audio_name = truth_row["audio_name"]
    artist = truth_row.get("artist", "").strip()
    title = truth_row.get("title", "").strip()

    # --- raw feature values from the pipeline extractor ---
    tempo_local = float(feats.get("tempo_bpm", 0.0) or 0.0)
    duration_sec = float(feats.get("duration_sec", 0.0) or 0.0)
    loudness = float(feats.get("loudness_LUFS", 0.0) or 0.0)
    raw_energy = feats.get("energy", None)
    raw_dance = feats.get("danceability", None)
    raw_valence = feats.get("valence", None)

    # --- truth values ---
    tempo_truth = float(truth_row.get("tempo_feel_bpm_truth") or 0.0)
    runtime_truth = truth_row.get("runtime_band_truth", "").strip() or "unknown"
    loudness_truth = truth_row.get("loudness_lufs_band_truth", "").strip() or "unknown"
    energy_truth = truth_row.get("energy_band_truth", "").strip() or "unknown"
    dance_truth = truth_row.get("dance_band_truth", "").strip() or "unknown"
    valence_truth = truth_row.get("valence_band_truth", "").strip() or "unknown"

    # --- band the local values ---
    runtime_band_local = band_runtime(duration_sec)
    loudness_band_local = band_loudness(loudness)
    energy_band_local = band_energy(raw_energy)
    dance_band_local = band_dance(raw_dance)
    valence_band_local = band_valence(raw_valence)

    # --- status flags ---
    tempo_diff = tempo_local - tempo_truth
    # Restore original forgiving feel-based tempo tolerance (~5 BPM).
    tempo_ok = abs(tempo_diff) <= 5.0

    runtime_ok = runtime_band_local == runtime_truth
    loudness_ok = loudness_band_local == loudness_truth
    energy_ok = energy_band_local == energy_truth
    dance_ok = dance_band_local == dance_truth
    valence_ok = valence_band_local == valence_truth

    result: Dict[str, Any] = {
        "audio_name": audio_name,
        "artist": artist,
        "title": title,
        "tempo_local": tempo_local,
        "tempo_truth": tempo_truth,
        "tempo_diff": tempo_diff,
        "tempo_ok": tempo_ok,
        "runtime_band_local": runtime_band_local,
        "runtime_band_truth": runtime_truth,
        "runtime_ok": runtime_ok,
        "loudness_local": loudness,
        "loudness_band_local": loudness_band_local,
        "loudness_band_truth": loudness_truth,
        "loudness_ok": loudness_ok,
        "energy_local": raw_energy,
        "energy_band_local": energy_band_local,
        "energy_band_truth": energy_truth,
        "energy_ok": energy_ok,
        "dance_local": raw_dance,
        "dance_band_local": dance_band_local,
        "dance_band_truth": dance_truth,
        "dance_ok": dance_ok,
        "valence_local": raw_valence,
        "valence_band_local": valence_band_local,
        "valence_band_truth": valence_truth,
        "valence_ok": valence_ok,
    }
    return result


# ---------------------------------------------------------------------------
# Automatic threshold calibration for 0-1 axes
# ---------------------------------------------------------------------------


def _collect_axis_samples(
    records: Sequence[Tuple[Dict[str, str], Dict[str, Any]]],
    axis: str,
) -> Tuple[List[float], List[str]]:
    """
    Collect (value, truth_band) samples for a given axis from all records.
    """
    values: List[float] = []
    bands: List[str] = []

    key_map = {
        "energy": ("energy", "energy_band_truth"),
        "dance": ("danceability", "dance_band_truth"),
        "valence": ("valence", "valence_band_truth"),
    }

    feat_key, truth_key = key_map[axis]

    for truth_row, feats in records:
        truth_band = truth_row.get(truth_key, "").strip()
        if not truth_band or truth_band == "unknown":
            continue
        v = feats.get(feat_key, None)
        if v is None:
            continue
        try:
            vf = float(v)
        except Exception:
            continue
        if not math.isfinite(vf):
            continue
        # Clamp to [0, 1] just to be safe
        vf = max(0.0, min(1.0, vf))
        values.append(vf)
        bands.append(truth_band)

    return values, bands


def _find_optimal_two_thresholds(
    values: List[float],
    bands: List[str],
    axis: str,
    default: Tuple[float, float],
) -> Tuple[float, float]:
    """
    Given a set of (value in [0,1], truth_band), search for two thresholds
    t_lo < t_hi that minimize misclassification into {lo, mid, hi}.

    This is a tiny grid search over the sorted unique values, so it's fast
    for our ~50-song benchmark.
    """
    if not values or not bands or len(values) != len(bands):
        return default

    data = sorted(zip(values, bands), key=lambda x: x[0])
    uniq_vals = sorted({v for v, _ in data})

    if len(uniq_vals) < 3:
        return default

    best_err = float("inf")
    best_pair: Optional[Tuple[float, float]] = None

    # Don't use absolute extremes as thresholds to avoid degenerate splits.
    for i in range(1, len(uniq_vals) - 1):
        for j in range(i + 1, len(uniq_vals)):
            t_lo = uniq_vals[i]
            t_hi = uniq_vals[j]

            # Require a minimum gap so lo/mid/hi remain meaningfully distinct.
            if t_hi - t_lo < 0.05:
                continue

            err = 0
            for v, band_truth in data:
                if v < t_lo:
                    band_pred = "lo"
                elif v < t_hi:
                    band_pred = "mid"
                else:
                    band_pred = "hi"
                if band_pred != band_truth:
                    err += 1

            if err < best_err:
                best_err = err
                best_pair = (t_lo, t_hi)

    if best_pair is None:
        return default

    t_lo, t_hi = best_pair
    # Slightly pad inward to reduce hypersensitivity to single boundary points.
    pad = 0.01
    t_lo = max(0.0, t_lo - pad)
    t_hi = min(1.0, t_hi + pad)

    print(
        f"[calibration] {axis}: thresholds ~= ({t_lo:.3f}, {t_hi:.3f}) "
        f"with ~{best_err} misclassifications out of {len(values)}",
    )

    return (t_lo, t_hi)


def calibrate_axis_thresholds(
    records: Sequence[Tuple[Dict[str, str], Dict[str, Any]]],
) -> None:
    """
    Use the current benchmark truth to calibrate thresholds for
    energy/danceability/valence.

    This does **not** change any on-disk files; it only updates the in-process
    globals ENERGY_THRESHOLDS, DANCE_THRESHOLDS, VALENCE_THRESHOLDS used
    by band_energy/band_dance/band_valence for this run.
    """
    global ENERGY_THRESHOLDS, DANCE_THRESHOLDS, VALENCE_THRESHOLDS

    # Start from defaults
    ENERGY_THRESHOLDS = DEFAULT_THRESHOLDS
    DANCE_THRESHOLDS = DEFAULT_THRESHOLDS
    VALENCE_THRESHOLDS = DEFAULT_THRESHOLDS

    # Collect samples per axis
    energy_vals, energy_bands = _collect_axis_samples(records, "energy")
    dance_vals, dance_bands = _collect_axis_samples(records, "dance")
    valence_vals, valence_bands = _collect_axis_samples(records, "valence")

    if energy_vals:
        ENERGY_THRESHOLDS = _find_optimal_two_thresholds(
            energy_vals, energy_bands, "energy", DEFAULT_THRESHOLDS
        )

    if dance_vals:
        DANCE_THRESHOLDS = _find_optimal_two_thresholds(
            dance_vals, dance_bands, "dance", DEFAULT_THRESHOLDS
        )

    if valence_vals:
        VALENCE_THRESHOLDS = _find_optimal_two_thresholds(
            valence_vals, valence_bands, "valence", DEFAULT_THRESHOLDS
        )

    print(
        "[calibration] final thresholds:\n"
        f"  energy : {ENERGY_THRESHOLDS}\n"
        f"  dance  : {DANCE_THRESHOLDS}\n"
        f"  valence: {VALENCE_THRESHOLDS}"
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def summarize(results: List[Dict[str, Any]]) -> str:
    """
    Build the human-readable benchmark report string.
    """
    total = len(results)

    tempo_ok = sum(1 for r in results if r["tempo_ok"])
    runtime_ok = sum(1 for r in results if r["runtime_ok"])
    loudness_ok = sum(1 for r in results if r["loudness_ok"])
    energy_ok = sum(1 for r in results if r["energy_ok"])
    dance_ok = sum(1 for r in results if r["dance_ok"])
    valence_ok = sum(1 for r in results if r["valence_ok"])

    def pct(x: int) -> float:
        return (100.0 * x / total) if total > 0 else 0.0

    lines: List[str] = []
    lines.append("=== MusicAdvisor Benchmark Check ===")
    lines.append(f"Total benchmark songs: {total}")
    lines.append("")
    lines.append("Axis-level accuracy:")
    lines.append(
        f"  Tempo       : {tempo_ok}/{total} OK ({pct(tempo_ok):5.1f}%)"
    )
    lines.append(
        f"  Runtime     : {runtime_ok}/{total} OK ({pct(runtime_ok):5.1f}%)"
    )
    lines.append(
        f"  Loudness    : {loudness_ok}/{total} OK ({pct(loudness_ok):5.1f}%)"
    )
    lines.append(
        f"  Energy      : {energy_ok}/{total} OK ({pct(energy_ok):5.1f}%)"
    )
    lines.append(
        f"  Danceability: {dance_ok}/{total} OK ({pct(dance_ok):5.1f}%)"
    )
    lines.append(
        f"  Valence     : {valence_ok}/{total} OK ({pct(valence_ok):5.1f}%)"
    )
    lines.append("")

    # Per-track breakdown
    for r in results:
        lines.append("-" * 72)
        lines.append(
            f"{r['artist']} \u2013 {r['title']}  [{r['audio_name']}]"
        )
        lines.append(
            f"  Tempo: local={r['tempo_local']:.2f}  truth={r['tempo_truth']:.2f}  "
            f"diff={r['tempo_diff']:.2f}  status={'OK' if r['tempo_ok'] else 'MISMATCH'}"
        )
        lines.append(
            f"  Runtime band: local={r['runtime_band_local']}  "
            f"truth={r['runtime_band_truth']}  "
            f"status={'OK' if r['runtime_ok'] else 'MISMATCH'}"
        )
        lines.append(
            f"  Loudness: {r['loudness_local']:.2f} LUFS  "
            f"band local={r['loudness_band_local']}  "
            f"truth={r['loudness_band_truth']}  "
            f"status={'OK' if r['loudness_ok'] else 'MISMATCH'}"
        )
        energy_val = r['energy_local']
        energy_str = "None" if energy_val is None else f"{float(energy_val):.3f}"
        lines.append(
            f"  Energy: {energy_str}  "
            f"band local={r['energy_band_local']}  "
            f"truth={r['energy_band_truth']}  "
            f"status={'OK' if r['energy_ok'] else 'MISMATCH'}"
        )
        dance_val = r['dance_local']
        dance_str = "None" if dance_val is None else f"{float(dance_val):.3f}"
        lines.append(
            f"  Dance : {dance_str}  "
            f"band local={r['dance_band_local']}  "
            f"truth={r['dance_band_truth']}  "
            f"status={'OK' if r['dance_ok'] else 'MISMATCH'}"
        )
        valence_val = r['valence_local']
        valence_str = "None" if valence_val is None else f"{float(valence_val):.3f}"
        lines.append(
            f"  Valence: {valence_str}  "
            f"band local={r['valence_band_local']}  "
            f"truth={r['valence_band_truth']}  "
            f"status={'OK' if r['valence_ok'] else 'MISMATCH'}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def evaluate_benchmark(truth_csv: Path, root: Path) -> str:
    """
    Load truth + features, auto-calibrate 0-1 thresholds for this benchmark,
    then build the full diff report as a string.
    """
    truth_rows: List[Dict[str, str]] = []
    with truth_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            truth_rows.append(row)

    records: List[Tuple[Dict[str, str], Dict[str, Any]]] = []
    missing: List[Tuple[str, str]] = []

    for row in truth_rows:
        audio_name = row["audio_name"]
        feat_path = find_features_json(root, audio_name)
        if feat_path is None:
            missing.append((audio_name, "No matching *.features.json found"))
            continue

        try:
            feats = load_json(feat_path)
        except Exception as e:
            missing.append((audio_name, f"Failed to load {feat_path}: {e}"))
            continue

        records.append((row, feats))

    if not records:
        return "No records to evaluate (no matching features files found)."

    # 1) Use current truth + features to calibrate thresholds for 0-1 axes.
    calibrate_axis_thresholds(records)

    # 2) Run comparisons with the calibrated thresholds.
    results: List[Dict[str, Any]] = []
    for truth_row, feats in records:
        res = compare_one(truth_row, feats)
        results.append(res)

    report = summarize(results)

    if missing:
        report += "\n\nMissing entries:\n"
        for name, msg in missing:
            report += f"  - {name}: {msg}\n"

    return report


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compare extracted features against benchmark_truth.csv"
    )
    parser.add_argument(
        "--truth",
        required=True,
        type=Path,
        help="Path to benchmark_truth.csv",
    )
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
        help="Root directory containing *.features.json files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional output report path (text file)",
    )

    args = parser.parse_args(argv)

    truth_csv = args.truth.expanduser().resolve()
    root = args.root.expanduser().resolve()

    report = evaluate_benchmark(truth_csv, root)

    # Always echo headline stats to stdout for quick checks.
    lines = report.splitlines()
    for line in lines[:8]:
        print(line)

    if args.out:
        out_path = args.out.expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[INFO] Full report written to: {out_path}")


if __name__ == "__main__":
    main()
