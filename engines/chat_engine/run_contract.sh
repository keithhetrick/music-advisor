#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/engines/chat_engine"

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
if [ -z "$PYTHON_BIN" ]; then
  echo "python3 not found on PATH" >&2
  exit 1
fi

PYTHONPATH="$ROOT" "$PYTHON_BIN" contract_smoke.py
PYTHONPATH="$ROOT" "$PYTHON_BIN" test_contract.py

echo "chat_engine contract: ok"
