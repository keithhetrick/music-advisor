#!/usr/bin/env python3
"""
Tiny helper to merge an external equilibrium payload onto an internal one.
Non-destructive: internal keys win.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ma_audio_engine.adapters import (
    add_log_sandbox_arg,
    apply_log_sandbox_env,
    load_json_guarded,
    require_file,
    utc_now_iso,
)
from shared.ma_utils.logger_factory import get_configured_logger


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge equilibrium internal+external payloads.")
    ap.add_argument("--internal", required=True, help="Primary payload (authoritative).")
    ap.add_argument("--external", help="Optional supplemental payload (non-destructive merge).")
    ap.add_argument("--out", required=True, help="Write merged JSON here.")
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    ap.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    global _log
    _log = get_configured_logger("equilibrium_merge")

    internal_path = Path(args.internal).expanduser().resolve()
    external_path = Path(args.external).expanduser().resolve() if args.external else None
    out_path = Path(args.out).expanduser().resolve()

    require_file(internal_path, desc="internal equilibrium payload")
    merged = load_json_guarded(internal_path, expect_mapping=True, logger=_log) or {}
    if external_path:
        require_file(external_path, desc="external equilibrium payload", is_dir=False, must_exist=False)
        if external_path.is_file():
            ext = load_json_guarded(external_path, expect_mapping=True, logger=_log)
            if ext:
                for k, v in ext.items():
                    merged.setdefault(k, v)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(merged, f, indent=2)

    _log(
        f"[equilibrium_merge] wrote {out_path} "
        f"(internal={internal_path}, external={external_path}) "
        f"finished_at={utc_now_iso()}Z"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
