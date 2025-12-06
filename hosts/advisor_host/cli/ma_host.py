#!/usr/bin/env python3
"""
Tiny CLI: read helper text or JSON payload, emit advisory JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from advisor_host.adapter.adapter import ParseError, parse_helper_text, parse_payload
from advisor_host.host.advisor import run_advisory, run_recommendation


def read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> None:
    ap = argparse.ArgumentParser(description="advisor host: helper text -> advisory/recommendation JSON")
    ap.add_argument("source", nargs="?", help="Path to helper text or JSON payload (defaults to stdin).")
    ap.add_argument("--norms", help="Optional path to market_norms_snapshot JSON to enable recommendation engine.")
    ap.add_argument("--save-session", help="Optional path to save session JSON after processing.")
    ap.add_argument("--load-session", help="Optional path to load session JSON before processing.")
    args = ap.parse_args()

    try:
        session = None
        if args.load_session:
            try:
                from advisor_host.host.session_store import load_session  # type: ignore
                session = load_session(Path(args.load_session))
            except Exception:
                session = None
        raw_text = read_input(args.source)
        payload = parse_payload(parse_helper_text(raw_text))
        if args.norms:
            norms = json.loads(Path(args.norms).read_text(encoding="utf-8"))
            output = run_recommendation(payload, norms)
            meta = {k: norms.get(k) for k in ("region", "tier", "version")}
            output["market_norms_used"] = meta
            if session:
                session.last_recommendation = output
        else:
            output = run_advisory(payload)
            output["market_norms_used"] = None
            if session:
                session.last_recommendation = output
        if args.save_session and session:
            try:
                from advisor_host.host.session_store import save_session  # type: ignore
                save_session(session, Path(args.save_session))
            except Exception:
                pass
        json.dump(output, sys.stdout, indent=2)
        sys.stdout.write("\n")
    except ParseError as exc:
        sys.stderr.write(f"[ERR] {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
