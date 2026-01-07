#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

forbidden=(
  "infra/scripts/smoke_full_chain.sh"
  "python tools/ma_orchestrator.py"
  "python3 tools/ma_orchestrator.py"
  "make hci-smoke"
)

ignore_globs=(
  "docs/repo_surgery/**"
  ".git/**"
)

fail=0
for pat in "${forbidden[@]}"; do
  if rg -n "$pat" docs README.md --glob '!.git' --glob '!docs/repo_surgery/**' --glob '!**/*.bak' >/tmp/frontdoor_hits.txt; then
    echo "[frontdoor] forbidden reference detected for pattern: $pat" >&2
    cat /tmp/frontdoor_hits.txt >&2
    fail=1
  fi
done
rm -f /tmp/frontdoor_hits.txt
if [ $fail -ne 0 ]; then
    echo "[frontdoor] FAIL: docs contain direct entrypoints; use ma_helper commands instead." >&2
    exit 1
fi
echo "[frontdoor] OK: docs reference ma_helper front door."
