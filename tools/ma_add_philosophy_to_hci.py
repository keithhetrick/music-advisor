#!/usr/bin/env python3
"""
ma_add_philosophy_to_hci.py

Inject a standard HCI_v1 philosophy block into all .hci.json files under a root.

- Adds or updates the "HCI_v1_philosophy" field in each .hci.json.
- This field is purely metadata and does NOT affect any numeric scores or axes.

Example:
    python tools/ma_add_philosophy_to_hci.py \
      --root features_output/2025/11/18

By default, existing HCI_v1_philosophy blocks are left as-is. Use --force to
overwrite them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import add_log_sandbox_arg, add_log_format_arg, add_preflight_arg, apply_log_sandbox_env, apply_log_format_env, run_preflight_if_requested
from ma_audio_engine.adapters import load_log_settings, load_runtime_settings
from ma_audio_engine.adapters import utc_now_iso
from ma_audio_engine.adapters import di
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from shared.ma_utils import get_configured_logger
from tools.philosophy_services import write_hci_with_philosophy, PHILOSOPHY_PAYLOAD


_log = get_configured_logger("add_philosophy_hci")


def main() -> None:
    ap = argparse.ArgumentParser(description="Inject HCI_v1 philosophy metadata into .hci.json files.")
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory to scan (e.g. features_output/2025/11/18)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing HCI_v1_philosophy blocks if present.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if lint warnings are present in modified HCI files.",
    )
    add_log_sandbox_arg(ap)
    add_log_format_arg(ap)
    add_preflight_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    apply_log_format_env(args)
    run_preflight_if_requested(args)
    # Load runtime settings to keep env/config defaults aligned.
    _ = load_runtime_settings(args)
    global _log
    _log = get_configured_logger("add_philosophy_hci", defaults={"tool": "add_philosophy_hci"})

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")
    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        _log("start", {"event": "start", "tool": "add_philosophy_hci", "root": str(root)})
        log_stage_start(_log, "add_philosophy_hci", root=str(root), force=bool(args.force))

    hci_files = sorted(root.rglob("*.hci.json"))
    if not hci_files:
        print(f"[INFO] No .hci.json files found under {root}")
        return

    changed = 0
    warnings: list[str] = []
    for p in hci_files:
        updated, warns = write_hci_with_philosophy(p, force=args.force)
        if updated:
            changed += 1
        warnings.extend(warns)

    timestamp = utc_now_iso()
    _log(f"[DONE] {timestamp} processed {len(hci_files)} .hci.json files; updated {changed} of them.")
    status = "ok"
    if warnings and args.strict:
        status = "error"
    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            _log,
            "add_philosophy_hci",
            status=status,
            root=str(root),
            processed=len(hci_files),
            updated=changed,
            duration_ms=duration_ms,
            warnings=warnings,
        )
        _log("end", {"event": "end", "tool": "add_philosophy_hci", "root": str(root), "status": status, "processed": len(hci_files), "updated": changed, "duration_ms": duration_ms, "warnings": warnings})

    if warnings and args.strict:
        raise SystemExit("strict mode: lint warnings present")


if __name__ == "__main__":
    main()
