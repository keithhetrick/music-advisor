#!/usr/bin/env python3
"""
Minimal chat CLI to mimic a backend-only chat experience.

Type a message, press Enter, and the script will call the configured chat handler
and print the response. This is intentionally lightweight and backend-only.

Configuration:
- Set CHAT_ENDPOINT to point to your local chat endpoint (HTTP) or adjust
  the `call_chat` function to import/call your in-process handler.
"""
from __future__ import annotations

import json
import sys
import urllib.request

# Adjust to your local chat endpoint
CHAT_ENDPOINT = "http://127.0.0.1:8000/chat"


def call_chat(message: str) -> str:
    """Call the chat endpoint with a simple JSON payload."""
    payload = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        CHAT_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            try:
                parsed = json.loads(data)
                return parsed.get("response", data)
            except Exception:
                return data
    except Exception as exc:
        return f"[error] {exc}"


def main() -> int:
    print("Chat CLI (backend-only). Ctrl+C to exit.")
    print(f"Endpoint: {CHAT_ENDPOINT}")
    while True:
        try:
            msg = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not msg:
            continue
        resp = call_chat(msg)
        print(f"bot> {resp}")


if __name__ == "__main__":
    sys.exit(main())
