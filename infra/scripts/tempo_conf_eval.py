#!/usr/bin/env python3
"""
Evaluate tempo estimates against ground truth for calibration.

Usage:
    python scripts/tempo_conf_eval.py --conf /tmp/tempo_conf_raw.csv --truth <truth_csv>
Defaults for truth resolve via env TEMPO_CONF_TRUTH or calibration root.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

import numpy as np
import pandas as pd

from adapters.cli_adapter import add_log_sandbox_arg, apply_log_sandbox_env
from adapters.logging_adapter import make_logger
from adapters.time_adapter import utc_now_iso
from ma_config.paths import get_calibration_root

_log = print


def normalize_stem(path: str) -> str:
    base = os.path.basename(str(path))
    # strip known extensions and sidecar suffixes repeatedly
    for _ in range(3):
        base = re.sub(r"\.(ess|mm|librosa)(\.json)?$", "", base)
        base = re.sub(r"\.(json|wav|mp3|flac|aiff|aif|m4a|aac|ogg)$", "", base)
    return base


def evaluate(conf_path: str, truth_path: str) -> Tuple[pd.DataFrame, List[str], List[str]]:
    conf = pd.read_csv(conf_path)
    truth = pd.read_csv(truth_path)
    conf["stem"] = conf["audio"].apply(normalize_stem)
    truth["stem"] = truth["audio_name"].apply(normalize_stem)
    truth_map = truth.set_index("stem")

    rows = []
    for _, row in conf.iterrows():
        stem = row["stem"]
        if stem not in truth_map.index:
            continue
        trow = truth_map.loc[stem]
        tempo = row["tempo"]
        truth_tempo = trow["tempo_feel_bpm_truth"] if "tempo_feel_bpm_truth" in trow else trow.get("tempo")
        if pd.isna(tempo) or pd.isna(truth_tempo):
            continue
        abs_err = abs(tempo - truth_tempo)
        rel_err = abs_err / truth_tempo if truth_tempo else np.nan
        half = abs(tempo * 2 - truth_tempo) <= 2
        double = abs(tempo / 2 - truth_tempo) <= 2
        within3bpm = abs_err <= 3
        within3pct = rel_err <= 0.03 if not pd.isna(rel_err) else False
        rows.append(
            {
                "backend": row["backend"],
                "abs_err": abs_err,
                "rel_err": rel_err,
                "half": half,
                "double": double,
                "within3bpm": within3bpm,
                "within3pct": within3pct,
            }
        )

    matched = pd.DataFrame(rows)
    conf_stems = set(conf["stem"])
    truth_stems = set(truth["stem"])
    miss_conf = sorted(conf_stems - truth_stems)
    miss_truth = sorted(truth_stems - conf_stems)
    return matched, miss_conf, miss_truth


def summarize(matched: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for backend, sub in matched.groupby("backend"):
        rows.append(
            {
                "backend": backend,
                "n": len(sub),
                "median_abs_err": round(sub["abs_err"].median(), 3),
                "mean_abs_err": round(sub["abs_err"].mean(), 3),
                "within_3bpm_pct": round(sub["within3bpm"].mean() * 100, 2),
                "within_3pct_pct": round(sub["within3pct"].mean() * 100, 2),
                "half_count": int(sub["half"].sum()),
                "double_count": int(sub["double"].sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate tempo estimates vs ground truth.")
    ap.add_argument("--conf", default="/tmp/tempo_conf_raw.csv", help="Path to harvested tempo conf CSV.")
    ap.add_argument(
        "--truth",
        default=None,
        help="Ground truth CSV (default honors env TEMPO_CONF_TRUTH; falls back to calibration root).",
    )
    ap.add_argument("--out", help="Optional path to write summary CSV.")
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    add_log_sandbox_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    redact_flag = args.log_redact or os.environ.get("LOG_REDACT", "0") == "1"
    redact_values = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
    _log = make_logger("tempo_conf_eval", use_rich=False, redact=redact_flag, secrets=redact_values)

    truth_path = (
        Path(args.truth)
        if args.truth
        else Path(os.getenv("TEMPO_CONF_TRUTH") or get_calibration_root() / "benchmark_truth_v1_1.csv")
    )
    matched, miss_conf, miss_truth = evaluate(args.conf, str(truth_path))
    summary = summarize(matched)

    _log(summary.to_string(index=False))
    if miss_conf:
        _log("\nUnmatched in truth (from conf): " + ", ".join(miss_conf))
    if miss_truth:
        _log("\nUnmatched in conf (from truth): " + ", ".join(miss_truth))

    if args.out:
        summary.to_csv(args.out, index=False)
        _log(f"\nWrote summary -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
