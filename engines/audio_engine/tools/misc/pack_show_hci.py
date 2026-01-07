#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from adapters import add_log_sandbox_arg, apply_log_sandbox_env
from adapters import make_logger
from adapters import utc_now_iso

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]


def show_one(p: Path, log) -> Dict[str, Any] | None:
    try:
        d = json.loads(p.read_text())
    except Exception as e:
        log(f"[pack_show_hci] bad json: {p} ({e})")
        return None
    name = d.get("audio_name") or p.stem
    hv1 = d.get("HCI_v1") or {}
    raw = hv1.get("HCI_v1_raw") or hv1.get("HCI_v1_score") or d.get("HCI_v1_score")
    cal = hv1.get("HCI_v1_calibrated")
    src = hv1.get("HCI_v1_source") or ("calibrated" if cal is not None else "raw")
    if raw is None and cal is None:
        print(f"{name:55s} HCI=NA (no data)")
        return None
    if cal is not None:
        print(f"{name:55s} HCI={cal:.3f}  (calibrated, raw={float(raw):.3f})")
    else:
        print(f"{name:55s} HCI={float(raw):.3f}  (raw)")
    return {
        "path": str(p),
        "audio_name": name,
        "hci_raw": raw,
        "hci_calibrated": cal,
        "source": src,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Show HCI scores from *.pack.json files.")
    ap.add_argument("root")
    ap.add_argument("--glob", default="**/*.pack.json")
    ap.add_argument("--json", action="store_true", help="emit json lines")
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
    redact_flag = args.log_redact or LOG_REDACT
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or LOG_REDACT_VALUES
    )
    log = make_logger("pack_show_hci", redact=redact_flag, secrets=redact_values)

    root = Path(args.root)
    files = sorted(root.rglob(args.glob))
    if not files:
        log(f"[pack_show_hci] not found: {root}/{args.glob}")
        sys.exit(1)

    if args.json:
        for p in files:
            res = show_one(p, log)
            if res is not None:
                print(json.dumps(res))
        return

    for p in files:
        show_one(p, log)


if __name__ == "__main__":
    main()
