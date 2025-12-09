#!/usr/bin/env python3
"""
Contract smoke: ensures chat_engine.run emits the expected JSON keys.
"""
from __future__ import annotations

import json
import sys
from chat_engine import ChatRequest, run


def main() -> int:
    req = ChatRequest(prompt="contract-smoke", context_path=None, label="test")
    res = run(req)
    data = json.loads(res.to_json())
    required = {"reply", "label", "warning", "rate_limited", "timed_out", "context_path"}
    missing = required - set(data.keys())
    if missing:
        print(f"Missing keys: {missing}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
