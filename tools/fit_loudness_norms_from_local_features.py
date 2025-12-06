#!/usr/bin/env python3
"""
tools/fit_loudness_norms_from_local_features.py

Derive loudness_mean / loudness_std for the LoudnessFit axis from local
.features.json files, and optionally emit:

  1) A small calibration JSON for bookkeeping.
  2) A new market_norms JSON with "MARKET_NORMS.loudness_mean/std" filled in.

This is intentionally simple and LOCAL-ONLY for now:

- It ignores Spotify/Kaggle features when computing norms.
- It just says: "Given this cohort of (usually hit) songs, what is the
  typical loudness_LUFS and spread that the pipeline sees?"

Later, when you have ~1600 songs (Top 40 from 1985 onward), you can re-run
this over the larger corpus to update the norms in a versioned way.

Typical workflow:

  1) Run this over your local cohort, e.g.:

       python tools/fit_loudness_norms_from_local_features.py \
         --features-root features_output/2025/11/22 \
         --years 1985 1986 \
         --calib-json calibration/loudness_norms_local_1985_1986_v1.json \
         --market-norms-in calibration/market_norms_us_pop.json \
         --market-norms-out calibration/market_norms_us_pop_loudness_v1.json

  2) Recompute axes using the *new* market norms:

       python tools/hci_recompute_axes_for_root.py \
         --root features_output/2025/11/22 \
         --market-norms calibration/market_norms_us_pop_loudness_v1.json

  3) Inspect LoudnessFit distribution on the .hci.json files
     (e.g. via a small debug script or your existing inline checker).
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Dict, Any, Iterable, List, Optional, Sequence

from ma_config.audio import (
    DEFAULT_LOUDNESS_NORMS_LOCAL_PATH,
    DEFAULT_MARKET_NORMS_PATH,
    resolve_market_norms,
    resolve_loudness_norms_out,
)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def _collect_lufs(
    features_root: Path,
    years_filter: Optional[Sequence[int]] = None,
) -> List[float]:
    """
    Walk features_root for *.features.json and collect loudness_LUFS values.

    Assumes structure like:
        features_root / <year> / <slug_dir> / *.features.json

    where <year> is an integer directory name (e.g. "1985", "1986").
    """
    years_set = set(int(y) for y in years_filter) if years_filter else None
    lufs_vals: List[float] = []

    for feat_path in sorted(features_root.rglob("*.features.json")):
        # Try to infer year from the directory path.
        rel = feat_path.relative_to(features_root)
        parts = rel.parts
        if not parts:
            continue

        try:
            year_candidate = int(parts[0])
        except Exception:
            # Not a year directory; skip if a years_filter is present.
            if years_set is not None:
                continue
            else:
                year_candidate = None

        if years_set is not None and year_candidate not in years_set:
            continue

        try:
            blob = _load_json(feat_path)
        except Exception:
            continue

        # Features may be flat or wrapped in {"features_full": {...}}.
        if isinstance(blob, dict) and "features_full" in blob:
            feats = blob.get("features_full") or {}
        else:
            feats = blob

        if not isinstance(feats, dict):
            continue

        raw = feats.get("loudness_LUFS")
        if isinstance(raw, (int, float)):
            lufs_vals.append(float(raw))

    return lufs_vals


def _compute_mean_std(vals: Sequence[float]) -> Optional[tuple[float, float]]:
    if not vals:
        return None
    if len(vals) == 1:
        # Degenerate case: single track
        return float(vals[0]), 1.0
    try:
        mean = float(statistics.mean(vals))
        std = float(statistics.stdev(vals))
    except Exception:
        return None
    if std <= 0.0:
        std = 1.0
    return mean, std


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Fit loudness_mean / loudness_std for LoudnessFit from local "
            ".features.json files, and optionally emit a patched market_norms JSON."
        )
    )
    ap.add_argument(
        "--features-root",
        required=True,
        help="Root directory for .features.json (e.g. features_output/2025/11/22)",
    )
    ap.add_argument(
        "--years",
        nargs="*",
        type=int,
        help="Optional list of years to include (e.g. 1985 1986). "
             "If omitted, use all years under features-root.",
    )
    ap.add_argument(
        "--calib-json",
        default=str(DEFAULT_LOUDNESS_NORMS_LOCAL_PATH),
        help="Where to write the loudness calibration JSON (default honors MA_CALIBRATION_ROOT).",
    )
    ap.add_argument(
        "--market-norms-in",
        help="Existing market_norms JSON to read (default honors env AUDIO_MARKET_NORMS or calibration/market_norms_us_pop.json). "
             "If provided with --market-norms-out, a patched copy will be emitted.",
    )
    ap.add_argument(
        "--market-norms-out",
        help="Output path for patched market_norms JSON with loudness_mean/std filled in (default honors AUDIO_LOUDNESS_NORMS_OUT or calibration/market_norms_us_pop_loudness_v1.json). "
             "Must not be the same as --market-norms-in.",
    )
    args = ap.parse_args()

    features_root = Path(args.features_root)
    if not features_root.exists():
        raise SystemExit(f"[ERROR] features-root does not exist: {features_root}")

    years_filter = args.years or None
    if years_filter:
        print(f"[INFO] Restricting to years: {sorted(set(years_filter))}")
    else:
        print("[INFO] Using ALL years present under features-root")

    # ------------------------------------------------------------------
    # 1) Collect local loudness_LUFS from features
    # ------------------------------------------------------------------
    lufs_vals = _collect_lufs(features_root, years_filter)
    count = len(lufs_vals)
    if count == 0:
        raise SystemExit(
            "[ERROR] No numeric loudness_LUFS values found under "
            f"{features_root} for the given year filter."
        )

    print(f"[INFO] Collected {count} loudness_LUFS values from local features.")

    stats = _compute_mean_std(lufs_vals)
    if stats is None:
        raise SystemExit("[ERROR] Could not compute mean/std for loudness_LUFS.")
    mean_lufs, std_lufs = stats

    print("")
    print("=== LOCAL LOUDNESS STATS (LUFS as seen by the pipeline) ===")
    print(f"mean loudness_LUFS : {mean_lufs:.3f}")
    print(f"std  loudness_LUFS : {std_lufs:.3f}")
    print("")

    # ------------------------------------------------------------------
    # 2) Write a small calibration JSON for bookkeeping
    # ------------------------------------------------------------------
    calib_path = Path(args.calib_json)
    calib_payload: Dict[str, Any] = {
        "cohort_id": "Local_Loudness_USPop_v1",
        "note": (
            "Local loudness norms for LoudnessFit, derived from .features.json "
            "via fit_loudness_norms_from_local_features.py"
        ),
        "features_root": str(features_root),
        "years": sorted(set(years_filter)) if years_filter else None,
        "n_tracks": count,
        "loudness_LUFS_mean": mean_lufs,
        "loudness_LUFS_std": std_lufs,
    }
    _save_json(calib_path, calib_payload)
    print(f"[INFO] Wrote loudness calibration JSON to: {calib_path}")
    print("")

    # ------------------------------------------------------------------
    # 3) Optionally emit a patched market_norms JSON
    # ------------------------------------------------------------------
    # Patch market norms if possible (use defaults when not provided)
    src = Path(args.market_norms_in) if args.market_norms_in else resolve_market_norms(None, log=lambda *_args, **_kwargs: None)[0]
    dst = Path(args.market_norms_out) if args.market_norms_out else resolve_loudness_norms_out(None)

    if src and dst:
        if not src.exists():
            print(f"[WARN] market-norms-in does not exist: {src} (skipping patch)")
        elif src.resolve() == dst.resolve():
            raise SystemExit("[ERROR] --market-norms-out must be different from --market-norms-in.")
        else:
            market = _load_json(src)
            mn = market.get("MARKET_NORMS")
            if not isinstance(mn, dict):
                raise SystemExit(f"[ERROR] MARKET_NORMS key missing or not a dict in {src}")

            mn["loudness_mean"] = mean_lufs
            mn["loudness_std"] = std_lufs

            _save_json(dst, market)
            print(f"[INFO] Wrote patched market norms with loudness_mean/std to: {dst}")
            print("")
            print("Suggested usage:")
            print("")
            print("  python tools/hci_recompute_axes_for_root.py \\")
            print(f"    --root {features_root} \\")
            print(f"    --market-norms {dst}")
            print("")
    else:
        print("[INFO] No market norms path available; only the loudness calibration JSON was written.")
        print("")
        print("To plug these norms into HCI_v1 LoudnessFit, add to your MARKET_NORMS block:")
        print("")
        print("  \"loudness_mean\": %.3f," % mean_lufs)
        print("  \"loudness_std\": %.3f" % std_lufs)
        print("")


if __name__ == "__main__":
    main()
