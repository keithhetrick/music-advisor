#!/usr/bin/env bash
set -euo pipefail
# Minimal CI-like runner for local/Quick Action use.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
./infra/scripts/quick_check.sh "$@"
