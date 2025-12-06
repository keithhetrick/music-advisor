#!/usr/bin/env bash
# Run FastAPI chat shim for advisor_host with optional PORT (default 8080).
set -euo pipefail

PORT=${PORT:-8080}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python3 -m uvicorn advisor_host.server:app --host 0.0.0.0 --port "$PORT"
