#!/usr/bin/env bash
# Run advisor_host tests if relevant files changed; fallback to always.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v git >/dev/null 2>&1; then
  ./scripts/with_repo_env.sh -m pytest hosts/advisor_host/tests
  exit 0
fi

CHANGED=$(git diff --name-only --cached HEAD || git diff --name-only HEAD)
if echo "$CHANGED" | grep -E 'hosts/advisor_host|tools/pack_writer.py'; then
  ./scripts/with_repo_env.sh -m pytest hosts/advisor_host/tests
else
  echo "[affected_host_tests] no host-related changes detected; skipping"
fi
