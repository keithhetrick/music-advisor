#!/usr/bin/env bash
# Smoke test: pipe a .client.txt or .client.json into ma-host and print advisory.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ $# -lt 1 ]; then
  echo "usage: scripts/smoke_ma_host.sh /path/to/client.txt|client.json" >&2
  exit 1
fi

SRC="$1"
if [ ! -f "$SRC" ]; then
  echo "[ERR] file not found: $SRC" >&2
  exit 1
fi

if [[ "$SRC" == *.json ]]; then
  ./scripts/with_repo_env.sh hosts/advisor_host/cli/ma_host.py "$SRC"
else
  cat "$SRC" | ./scripts/with_repo_env.sh hosts/advisor_host/cli/ma_host.py
fi
