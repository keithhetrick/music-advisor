#!/usr/bin/env python3
"""
backfill_features_meta.py

Scan a root for *.features.json and optionally re-extract to fill missing
metadata (hash, QA, tempo confidence, freshness). Default is read-only and
reports files that are missing core meta. Use --apply to regenerate in place.

Non-destructive defaults:
- Dry (report only) unless --apply is set.
- Atomic replace with .bak backup when applying.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
import os

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env
from ma_audio_engine.adapters import make_logger
from ma_audio_engine.adapters import utc_now_iso
from ma_audio_engine.adapters.bootstrap import ensure_repo_root
from ma_audio_features import analyze_pipeline
from ma_config.paths import get_features_output_root, get_repo_root

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
_log = make_logger("backfill_features_meta", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)
ensure_repo_root()


def needs_backfill(data: Dict[str, Any]) -> bool:
    required = [
        "source_hash",
        "qa_gate",
        "tempo_confidence",
        "tempo_confidence_score",
    ]
    for key in required:
        if key not in data or data.get(key) in (None, "", "unknown"):
            return True
    qa = data.get("qa") or {}
    if not qa.get("gate"):
        return True
    return False


def backfill_file(path: Path, apply: bool, thresholds: argparse.Namespace) -> bool:
    try:
        data = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        _log(f"[backfill] ERROR reading {path}: {e}")
        return False

    if not needs_backfill(data):
        return False

    source_audio = data.get("source_audio")
    if not source_audio:
        _log(f"[backfill] WARN missing source_audio in {path}, skipping.")
        return False

    _log(f"[backfill] Needs meta: {path}")
    if not apply:
        return True

    try:
        refreshed = analyze_pipeline(
            path=source_audio,
            cache_dir=thresholds.cache_dir,
            cache_backend=thresholds.cache_backend,
            use_cache=thresholds.use_cache,
            force=True,
            clip_peak_threshold=thresholds.clip_peak_threshold,
            silence_ratio_threshold=thresholds.silence_ratio_threshold,
            low_level_dbfs_threshold=thresholds.low_level_dbfs_threshold,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"[backfill] ERROR re-extracting {source_audio}: {e}")
        return False

    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(refreshed, indent=2))
    tmp.replace(path)
    _log(f"[backfill] Updated {path} (backup at {bak})")
    return True


def main() -> None:
    default_root = get_features_output_root()
    default_cache = Path(os.getenv("MA_CACHE_DIR", get_repo_root() / ".ma_cache"))
    p = argparse.ArgumentParser(description="Backfill missing meta in *.features.json (safe defaults: report-only).")
    p.add_argument(
        "--root",
        default=str(default_root),
        help=f"Root folder to scan (default: env MA_DATA_ROOT + features_output, i.e., {default_root}).",
    )
    p.add_argument("--apply", action="store_true", help="Regenerate in place when missing meta is found (default: report-only).")
    p.add_argument(
        "--cache-dir",
        default=str(default_cache),
        help=f"Cache dir for re-extraction (default: env MA_CACHE_DIR or {default_cache}).",
    )
    p.add_argument("--cache-backend", choices=["disk", "noop"], default="disk", help="Cache backend to use during refresh (disk or noop).")
    p.add_argument("--no-cache", action="store_true", help="Disable cache during re-extraction.")
    p.add_argument("--clip-peak-threshold", type=float, default=0.999, help="Clipping peak threshold.")
    p.add_argument("--silence-ratio-threshold", type=float, default=0.9, help="Silence ratio threshold.")
    p.add_argument("--low-level-dbfs-threshold", type=float, default=-40.0, help="Low-level dBFS threshold.")
    p.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    p.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(p)
    args = p.parse_args()

    apply_log_sandbox_env(args)
    redact_flag = args.log_redact or LOG_REDACT
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or LOG_REDACT_VALUES
    )
    global _log
    _log = make_logger("backfill_features_meta", redact=redact_flag, secrets=redact_values)

    root = Path(args.root)
    if not root.exists():
        raise FileNotFoundError(f"Root not found: {root}")

    found: List[Path] = sorted(root.rglob("*.features.json"))
    if not found:
        _log(f"[backfill] No *.features.json under {root}")
        return

    need_count = 0
    for path in found:
        changed = backfill_file(
            path,
            apply=args.apply,
            thresholds=argparse.Namespace(
                cache_dir=args.cache_dir,
                cache_backend=args.cache_backend,
                use_cache=not args.no_cache,
                clip_peak_threshold=args.clip_peak_threshold,
                silence_ratio_threshold=args.silence_ratio_threshold,
                low_level_dbfs_threshold=args.low_level_dbfs_threshold,
            ),
        )
        need_count += 1 if changed else 0

    mode = "APPLIED" if args.apply else "REPORT"
    _log(f"[backfill] {mode}: {need_count} file(s) needed meta refresh under {root} @ {utc_now_iso()}")


if __name__ == "__main__":
    main()
