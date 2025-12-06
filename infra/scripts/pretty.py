#!/usr/bin/env python3
# scripts/pretty.py
import json, sys, os
from pathlib import Path

from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from adapters.cli_adapter import add_log_sandbox_arg, apply_log_sandbox_env
from adapters.logging_adapter import make_logger

def main():
    ap = None
    _log = print
    if len(sys.argv) >= 2 and sys.argv[1].startswith("--"):
        import argparse
        ap = argparse.ArgumentParser(description="Pretty-print pack or advisory JSON.")
        ap.add_argument("json", help="pack.json or advisory.json")
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
        _log = make_logger("pretty", use_rich=False, redact=redact_flag, secrets=redact_values)
        path_arg = args.json
    else:
        if len(sys.argv) < 2:
            print("usage: scripts/pretty.py <pack_or_advisory.json>")
            return 1
        path_arg = sys.argv[1]

    p = Path(path_arg)
    d = json.loads(p.read_text())
    if "HCI_v1" in d:   # pack.json
        ff = d.get("features_full", {})
        _log(json.dumps({
          "HCI": d.get("HCI_v1",{}).get("HCI_v1_score"),
          "Axes": d.get("audio_axes"),
          "bpm": ff.get("bpm"),
          "key": ff.get("key"),
          "mode": ff.get("mode"),
          "duration_sec": ff.get("duration_sec"),
          "loudness_lufs": ff.get("loudness_lufs")
        }, indent=2))
    else:
        # advisory.json from smoke
        b=d.get("Baseline",{})
        adv=b.get("advisory",{})
        _log(json.dumps({
          "HCI": d.get("HCI_v1",{}).get("HCI_v1_score"),
          "BaselineID": b.get("id"),
          "Has_MARKET_NORMS": bool(b.get("MARKET_NORMS")),
          "Has_Advisory": "advisory" in b,
          "Market_Fit": adv.get("Market_Fit"),
          "Tempo": adv.get("tempo"),
          "Key": adv.get("key"),
          "Runtime": adv.get("runtime")
        }, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
