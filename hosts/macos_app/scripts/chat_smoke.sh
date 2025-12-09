#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$(cd "$APP_DIR/../.." && pwd)"

echo "== Building macOS app (Debug) =="
HOME="$APP_DIR/build/home" SWIFTPM_DISABLE_SANDBOX=1 swift build \
  --package-path "$APP_DIR" \
  --scratch-path "$APP_DIR/build/.swiftpm" \
  --disable-sandbox

echo "== Chat engine smoke =="
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
if [ -z "$PYTHON_BIN" ]; then
  echo "python3 not found on PATH" >&2
  exit 1
fi
PYTHONPATH="$ROOT" "$PYTHON_BIN" "$ROOT/engines/chat_engine/chat_cli.py" "$@"
# Contract checks (fail if contract breaks)
PYTHONPATH="$ROOT" "$PYTHON_BIN" "$ROOT/engines/chat_engine/contract_smoke.py"
PYTHONPATH="$ROOT" "$PYTHON_BIN" "$ROOT/engines/chat_engine/test_contract.py"

echo "Done."
