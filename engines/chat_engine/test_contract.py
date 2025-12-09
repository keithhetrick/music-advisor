"""
Minimal contract test for chat_engine JSON output.

Run manually:
  PYTHONPATH=.. python test_contract.py
"""
from __future__ import annotations

import json

from pathlib import Path
import sys

# Ensure repo root on path so tools/chat is importable when run directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chat_engine import ChatRequest, run


def test_contract():
    req = ChatRequest(prompt="hello-contract", context_path=None, label="test")
    res = run(req)
    data = json.loads(res.to_json())
    required = {"reply", "label", "warning", "rate_limited", "timed_out", "context_path"}
    missing = required - set(data.keys())
    assert not missing, f"Missing keys: {missing}"
    assert isinstance(data["reply"], str)
    assert isinstance(data["label"], str)
    assert isinstance(data["rate_limited"], bool)
    assert isinstance(data["timed_out"], bool)


if __name__ == "__main__":
    test_contract()
    print("ok")
