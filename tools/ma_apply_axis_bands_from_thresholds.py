# tools/ma_apply_axis_bands_from_thresholds.py
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Optional

# When running as:
#   python tools/ma_apply_axis_bands_from_thresholds.py ...
# modules inside tools/ are imported without the "tools." prefix.
import aee_band_thresholds as band


def _parse_float(value: Optional[str]) -> Optional[float]:
    """Safe float parser – returns None if value is empty or invalid."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _maybe_print_thresholds(thresholds: dict) -> None:
    """
    Best-effort pretty-print of thresholds, handling the fact that the JSON
    is a plain dict like:

      {
        "energy_feature": {"lo": ..., "hi": ..., ...},
        "danceability_feature": {"lo": ..., "hi": ..., ...}
      }

    or possibly:

      {
        "energy": {"lo": ..., "hi": ...},
        "danceability": {"lo": ..., "hi": ...}
      }
    """
    def _get_block(main_key: str, fallback_key: str) -> Optional[dict]:
        if isinstance(thresholds, dict):
            if main_key in thresholds and isinstance(thresholds[main_key], dict):
                return thresholds[main_key]
            if fallback_key in thresholds and isinstance(thresholds[fallback_key], dict):
                return thresholds[fallback_key]
        return None

    e_block = _get_block("energy_feature", "energy")
    d_block = _get_block("danceability_feature", "danceability")

    try:
        if e_block and "lo" in e_block and "hi" in e_block:
            print(
                f"       energy_feature: lo<{float(e_block['lo']):.6f}, "
                f"hi>{float(e_block['hi']):.6f}"
            )
        if d_block and "lo" in d_block and "hi" in d_block:
            print(
                f"       danceability_feature: lo<{float(d_block['lo']):.6f}, "
                f"hi>{float(d_block['hi']):.6f}"
            )
    except Exception:
        # Don't let logging kill the script if something is weird.
        pass


def apply_bands_to_csv(
    in_csv: Path,
    out_csv: Path,
    thresholds_path: Optional[Path] = None,
) -> None:
    """
    Read a CSV with energy_feature / danceability_feature columns,
    apply calibrated thresholds, and write out a new CSV with:

      - energy_feature_band
      - danceability_feature_band
    """
    if not in_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {in_csv}")

    # This returns a plain dict (JSON) of thresholds.
    thresholds = band.load_thresholds(thresholds_path)
    print(f"[INFO] Loaded thresholds from {thresholds_path or 'default'}")
    _maybe_print_thresholds(thresholds)

    with in_csv.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        input_fieldnames = reader.fieldnames or []

        # Ensure our new columns exist in the field order
        fieldnames = list(input_fieldnames)
        for col in ("energy_feature_band", "danceability_feature_band"):
            if col not in fieldnames:
                fieldnames.append(col)

        rows_out = []
        n_rows = 0

        for row in reader:
            n_rows += 1

            e_val = _parse_float(row.get("energy_feature"))
            d_val = _parse_float(row.get("danceability_feature"))

            if e_val is not None:
                row["energy_feature_band"] = band.get_energy_band(
                    e_val, thresholds=thresholds
                )
            else:
                row["energy_feature_band"] = ""

            if d_val is not None:
                row["danceability_feature_band"] = band.get_dance_band(
                    d_val, thresholds=thresholds
                )
            else:
                row["danceability_feature_band"] = ""

            rows_out.append(row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"[OK] Wrote {n_rows} rows to {out_csv}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Apply calibrated energy/dance band thresholds to a CSV and "
            "add `energy_feature_band` / `danceability_feature_band` columns."
        )
    )
    ap.add_argument(
        "--csv",
        required=True,
        help="Input CSV (e.g. calibration/aee_ml_reports/truth_vs_ml_v1_1.csv)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV path (will be created/overwritten).",
    )
    ap.add_argument(
        "--thresholds",
        default=None,
        help=(
            "Optional thresholds JSON path "
            "(default: calibration/aee_band_thresholds_v1_1.json)"
        ),
    )

    args = ap.parse_args()

    in_csv = Path(args.csv)
    out_csv = Path(args.out)
    thresholds_path = Path(args.thresholds) if args.thresholds else None

    apply_bands_to_csv(in_csv=in_csv, out_csv=out_csv, thresholds_path=thresholds_path)


if __name__ == "__main__":
    main()
