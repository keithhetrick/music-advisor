#!/usr/bin/env python3
"""
Session save/load utility for advisor_host chat.

Usage:
  python -m advisor_host.cli.session_cli --save /tmp/session.json --message "..." [--norms path] [--payload path]
  python -m advisor_host.cli.session_cli --load /tmp/session.json --message "more"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from advisor_host.adapter.adapter import ParseError, parse_helper_text, parse_payload
from advisor_host.host.chat import ChatSession, handle_message
from advisor_host.session.session_store import load_session, save_session


def main() -> None:
    ap = argparse.ArgumentParser(description="advisor host: chat with session persistence")
    ap.add_argument("--save", help="Path to save session JSON after handling message")
    ap.add_argument("--load", help="Path to load session JSON before handling message")
    ap.add_argument("--message", required=True, help="User message to process")
    ap.add_argument("--payload", help="Optional helper text/JSON path to parse as /audio payload")
    ap.add_argument("--norms", help="Optional market_norms snapshot JSON")
    ap.add_argument("--profile", default=None, help="Host profile to use (overrides session profile)")
    args = ap.parse_args()

    if args.load:
        session = load_session(Path(args.load))
    else:
        session = ChatSession()
    if args.profile:
        session.host_profile_id = args.profile

    payload = None
    if args.payload:
        try:
            raw_text = Path(args.payload).read_text(encoding="utf-8")
            payload = parse_payload(parse_helper_text(raw_text))
        except ParseError as exc:
            raise SystemExit(f"[ERR] {exc}") from exc

    norms = None
    if args.norms:
        norms = json.loads(Path(args.norms).read_text(encoding="utf-8"))

    resp = handle_message(session, args.message, payload=payload, market_norms_snapshot=norms)
    print(json.dumps(resp, indent=2))

    if args.save:
        save_session(session, Path(args.save))


if __name__ == "__main__":
    main()
