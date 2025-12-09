#!/usr/bin/env python3
"""
Simple JSON-emitting CLI for the chat engine.

Usage:
  python chat_cli.py --prompt "Hello" [--context /path/to/file.client.rich.txt] [--label macos-app] [--rate-limit 2.0] [--timeout 10.0]
"""

from __future__ import annotations

import argparse
import json
import sys

from chat_engine import ChatRequest, run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Chat engine CLI (JSON out)")
    parser.add_argument("--prompt", required=True, help="Prompt to send")
    parser.add_argument("--context", default=None, help="Path to .client.rich.txt")
    parser.add_argument("--label", default="No context", help="Context label")
    parser.add_argument("--rate-limit", type=float, default=0.0, help="Rate limit seconds")
    parser.add_argument("--timeout", type=float, default=0.0, help="Timeout seconds")
    args = parser.parse_args(argv)

    req = ChatRequest(
        prompt=args.prompt,
        context_path=args.context,
        label=args.label,
        rate_limit_seconds=args.rate_limit,
        timeout_seconds=args.timeout,
    )
    res = run(req)
    print(res.to_json())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
