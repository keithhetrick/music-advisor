#!/usr/bin/env python
import csv
import argparse
import os
from pathlib import Path
from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from adapters import add_log_sandbox_arg, apply_log_sandbox_env
from adapters import make_logger
from adapters import utc_now_iso


def finalize_truth(in_csv: str, out_csv: str) -> None:
    in_path = Path(in_csv)
    out_path = Path(out_csv)

    if not in_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {in_path}")

    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        required = [
            "energy_truth_final_band",
            "dance_truth_final_band",
        ]
        for col in required:
            if col not in fieldnames:
                raise ValueError(
                    f"Missing required column '{col}' in {in_path}. "
                    "Did you run ma_truth_vs_ml_add_review_columns.py and do the manual review?"
                )

        rows_out = []
        for row in reader:
            # Use the manually reviewed / corrected bands as the canonical truth
            row["energy_truth"] = (row.get("energy_truth_final_band") or "").strip()
            row["dance_truth"] = (row.get("dance_truth_final_band") or "").strip()
            rows_out.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    _log(f"[OK] Wrote finalized truth CSV to {out_path}")
    _log("     energy_truth <- energy_truth_final_band")
    _log("     dance_truth  <- dance_truth_final_band")


def main():
    parser = argparse.ArgumentParser(
        description="Finalize human-reviewed truth bands into legacy energy_truth/dance_truth columns."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Input CSV (e.g., truth_vs_ml_review_v1_1.csv)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output CSV (e.g., truth_vs_ml_final_v1_1.csv)",
    )
    parser.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    parser.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(parser)
    args = parser.parse_args()

    apply_log_sandbox_env(args)

    redact_env = os.getenv("LOG_REDACT", "0") == "1"
    redact_values_env = [v for v in (os.getenv("LOG_REDACT_VALUES") or "").split(",") if v]
    redact_flag = args.log_redact or redact_env
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or redact_values_env
    )
    global _log
    _log = make_logger("truth_finalize", use_rich=False, redact=redact_flag, secrets=redact_values)

    finalize_truth(args.csv, args.out)
    _log(f"[DONE] Finished at {utc_now_iso()}")


if __name__ == "__main__":
    main()
