#!/usr/bin/env python3
"""
Simple smoke test for chat_engine: runs a single prompt with an optional context path.
Usage:
  python engines/chat_engine/cli_smoke.py --prompt "Hi" [--context /path/to/client.rich.txt]
"""

import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.chat_engine.chat_engine import ChatRequest, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--context", help="Path to .client.rich.txt")
    args = parser.parse_args()

    req = ChatRequest(prompt=args.prompt, context_path=args.context, label="smoke")
    res = run(req)
    print("label:", res.label)
    print("warning:", res.warning)
    print("rate_limited:", res.rate_limited)
    print("timed_out:", res.timed_out)
    print("reply:", res.reply)


if __name__ == "__main__":
    main()
