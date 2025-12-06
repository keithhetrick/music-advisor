#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# We standardize on these 6 axes for the "raw" HCI_v1 signal.
AXIS_KEYS = [
    "TempoFit",
    "RuntimeFit",
    "LoudnessFit",
    "Energy",
    "Danceability",
    "Valence",
]


def clamp01(x: float) -> float:
    """Clamp a numeric value into [0.0, 1.0]."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def iter_hci_files(root: Path) -> List[Path]:
    """Return all *.hci.json files under a root directory."""
    if not root.exists():
        return []
    return [p for p in root.rglob("*.hci.json") if p.is_file()]


def axes_mean_from_dict(axes: Any) -> Optional[float]:
    """
    Compute the mean of the 6 canonical axes from a dict
    (TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence).

    Returns None if axes is not usable.
    """
    if not isinstance(axes, dict):
        return None
    vals: List[float] = []
    for key in AXIS_KEYS:
        v = axes.get(key)
        if v is None:
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


def _extract_axes_mean_from_any(data: Dict[str, Any]) -> Optional[float]:
    """
    Try to compute an axes mean from either:
      - data["axes"] (new style dict),
      - data["audio_axes"] (old style dict or list of 6 floats).
    """
    # New style: dict under "axes"
    if "axes" in data:
        m = axes_mean_from_dict(data["axes"])
        if m is not None:
            return m

    # Legacy style: "audio_axes" might be dict or list
    if "audio_axes" in data:
        axes = data["audio_axes"]
        if isinstance(axes, dict):
            m = axes_mean_from_dict(axes)
            if m is not None:
                return m
        elif isinstance(axes, list):
            vals: List[float] = []
            for v in axes:
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    continue
            if vals:
                return sum(vals) / len(vals)

    return None


def extract_raw_from_record(data: Dict[str, Any]) -> Optional[float]:
    """
    Heuristically extract the "raw" HCI_v1 signal from an .hci.json record.

    Preference order:
      1. Explicit HCI_v1_score_raw / HCI_v1.raw inside data["HCI_v1"].
      2. Top-level HCI_v1_score_raw.
      3. HCI_audio_v2.raw (legacy).
      4. Mean of the 6 axes (axes or audio_axes).

    IMPORTANT PATCH:
      - If any of the explicit candidates is 0.0 but the axes have
        non-zero values, we fall back to the axes mean instead of
        treating 0.0 as a real "no echo" signal.
    """
    # 1) Look inside HCI_v1 dict
    hci_block = data.get("HCI_v1")
    candidates: List[float] = []

    if isinstance(hci_block, dict):
        if "HCI_v1_score_raw" in hci_block:
            try:
                candidates.append(float(hci_block["HCI_v1_score_raw"]))
            except (TypeError, ValueError):
                pass
        if "raw" in hci_block:
            try:
                candidates.append(float(hci_block["raw"]))
            except (TypeError, ValueError):
                pass

    # 2) Top-level HCI_v1_score_raw
    if "HCI_v1_score_raw" in data:
        try:
            candidates.append(float(data["HCI_v1_score_raw"]))
        except (TypeError, ValueError):
            pass

    # 3) Legacy HCI_audio_v2.raw
    if "HCI_audio_v2" in data and isinstance(data["HCI_audio_v2"], dict):
        raw_v2 = data["HCI_audio_v2"].get("raw")
        if raw_v2 is not None:
            try:
                candidates.append(float(raw_v2))
            except (TypeError, ValueError):
                pass

    # 4) Try axes mean as a fallback
    axes_mean = _extract_axes_mean_from_any(data)

    # If we have explicit candidates, but they're all <= 0 and we DO
    # have meaningful axes, treat that as a "missing" raw and use axes.
    if candidates:
        # Keep positive candidates first
        for v in candidates:
            if v > 0.0:
                return v
        # All candidates are <= 0.0. If axes have structure, prefer axes.
        if axes_mean is not None and axes_mean > 0.0:
            return axes_mean
        # Otherwise, just return the first candidate (may be 0.0).
        return candidates[0]

    # No candidates at all; if we have axes, use them.
    if axes_mean is not None:
        return axes_mean

    # Truly nothing we can use.
    return None


def load_calibration(path: Path) -> Dict[str, float]:
    """
    Load a calibration JSON file.

    We allow a few shapes:
      - Top-level with the keys directly.
      - {"calibration": {...}}
      - {"meta": {"calibration": {...}}}
    """
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)

    cal = obj
    if isinstance(obj, dict):
        if "calibration" in obj and isinstance(obj["calibration"], dict):
            cal = obj["calibration"]
        if (
            "meta" in obj
            and isinstance(obj["meta"], dict)
            and "calibration" in obj["meta"]
            and isinstance(obj["meta"]["calibration"], dict)
        ):
            cal = obj["meta"]["calibration"]

    raw_mean = float(cal["raw_mean"])
    raw_std = float(cal.get("raw_std", 1e-6)) or 1e-6
    target_mean = float(cal.get("target_mean", 0.7))
    target_std = float(cal.get("target_std", 0.18))

    return {
        "scheme": cal.get("scheme", "zscore_linear_v1"),
        "raw_mean": raw_mean,
        "raw_std": max(raw_std, 1e-6),
        "target_mean": target_mean,
        "target_std": target_std,
    }


def apply_calibration_to_raw(raw: float, calib: Dict[str, float]) -> float:
    """
    Apply the z-score based linear mapping, then clamp to [0, 1].
    """
    raw_clamped = clamp01(raw)
    mu = calib["raw_mean"]
    sigma = calib["raw_std"]
    t_mu = calib["target_mean"]
    t_sigma = calib["target_std"]

    z = (raw_clamped - mu) / sigma
    score = t_mu + z * t_sigma
    return clamp01(score)


def fit_calibration(root: Path, out_path: Path, role: Optional[str] = None) -> None:
    """
    Fit a z-score calibration from a directory of .hci.json files.

    role: if provided, only include files where HCI_v1_role == role.
    """
    hci_files = iter_hci_files(root)
    raws: List[float] = []

    for p in hci_files:
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if role:
            if data.get("HCI_v1_role") != role:
                continue

        raw_val = extract_raw_from_record(data)
        if raw_val is None:
            continue
        raws.append(float(raw_val))

    if not raws:
        print(f"[ERROR] No usable raw values found under {root}", file=sys.stderr)
        sys.exit(1)

    raw_mean = float(statistics.mean(raws))
    raw_std = float(statistics.pstdev(raws)) or 1e-6

    calib = {
        "scheme": "zscore_linear_v1",
        "raw_mean": raw_mean,
        "raw_std": raw_std,
        "target_mean": 0.7,
        "target_std": 0.18,
        "n": len(raws),
        "role_filter": role or "",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(calib, f, indent=2, sort_keys=True)

    print(
        f"[OK] Wrote calibration to {out_path} "
        f"(n={len(raws)}, raw_mean={raw_mean:.3f}, raw_std={raw_std:.3f})"
    )


def apply_calibration_to_dir(root: Path, calib: Dict[str, float]) -> None:
    """
    Apply a calibration to all .hci.json files under root.

    - Uses extract_raw_from_record() to find a usable raw.
    - Writes back:
        HCI_v1.meta.calibration
        HCI_v1.raw
        HCI_v1.score
        HCI_v1_score_raw
        HCI_v1_score
    """
    hci_files = iter_hci_files(root)
    if not hci_files:
        print(f"[WARN] No .hci.json files under {root}", file=sys.stderr)
        return

    for p in hci_files:
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to read {p}: {e}", file=sys.stderr)
            continue

        raw_val = extract_raw_from_record(data)
        if raw_val is None:
            print(f"[WARN] No usable raw signal in {p}; skipping", file=sys.stderr)
            continue

        raw_clamped = clamp01(raw_val)
        score = apply_calibration_to_raw(raw_clamped, calib)

        hci_block = data.get("HCI_v1")
        if not isinstance(hci_block, dict):
            hci_block = {}
            data["HCI_v1"] = hci_block

        meta = hci_block.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            hci_block["meta"] = meta

        meta["calibration"] = {
            "scheme": calib["scheme"],
            "raw_mean": calib["raw_mean"],
            "raw_std": calib["raw_std"],
            "target_mean": calib["target_mean"],
            "target_std": calib["target_std"],
        }

        # Store in both the nested block and at the top level for compatibility.
        hci_block["raw"] = raw_clamped
        hci_block["score"] = score
        hci_block["HCI_v1_score_raw"] = raw_clamped
        hci_block["HCI_v1_score_calibrated"] = score

        data["HCI_v1_score_raw"] = raw_clamped
        data["HCI_v1_score"] = score

        try:
            with p.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        except Exception as e:
            print(f"[WARN] Failed to write {p}: {e}", file=sys.stderr)
            continue

    print(f"[DONE] Applied calibration to {len(hci_files)} file(s) under {root}")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="hci_calibration.py",
        description="Fit or apply HCI_v1 z-score calibration.",
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # fit subcommand
    p_fit = subparsers.add_parser("fit", help="Fit calibration from .hci.json files")
    p_fit.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Root directory containing .hci.json files",
    )
    p_fit.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output calibration JSON file",
    )
    p_fit.add_argument(
        "--role",
        type=str,
        default=None,
        help="Optional HCI_v1_role filter (e.g. 'benchmark')",
    )

    # apply subcommand
    p_apply = subparsers.add_parser("apply", help="Apply calibration to .hci.json files")
    p_apply.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Root directory containing .hci.json files",
    )
    p_apply.add_argument(
        "--calib",
        type=Path,
        required=True,
        help="Calibration JSON file (from 'fit' or existing)",
    )

    args = parser.parse_args(argv)

    if args.cmd == "fit":
        fit_calibration(args.root, args.out, role=args.role)
    elif args.cmd == "apply":
        calib = load_calibration(args.calib)
        apply_calibration_to_dir(args.root, calib)
    else:
        parser.error(f"Unknown subcommand: {args.cmd}")


if __name__ == "__main__":
    main()
