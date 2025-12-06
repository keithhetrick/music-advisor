#!/usr/bin/env bash
set -euo pipefail
# Lightweight helper layer self-checks (no pytest deps).

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

PY_BIN="${PY_BIN:-python3}"
exec "$PY_BIN" tests/helper/self_check.py "$@"
