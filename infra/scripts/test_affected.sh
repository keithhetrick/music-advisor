#!/usr/bin/env bash
set -euo pipefail

# Lightweight "affected tests" helper. Tries to run the smallest useful test set
# based on changed paths. Falls back to make quick-check when unsure.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Resolve changed files
BASE_REF="${BASE_REF:-origin/main}"
if git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  CHANGED="$(git diff --name-only "${BASE_REF}"...HEAD || true)"
else
  CHANGED="$(git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only || true)"
fi

# If nothing reported, fall back to working tree changes
if [ -z "${CHANGED}" ]; then
  CHANGED="$(git status --porcelain | awk '{print $2}')"
fi

declare -a RUN_CMDS=()

maybe_add() {
  local pattern="$1"; shift
  local cmd="$*"
  if echo "${CHANGED}" | grep -E "${pattern}" >/dev/null 2>&1; then
    RUN_CMDS+=("${cmd}")
  fi
}

# Map directories to focused test commands
maybe_add '^engines/audio_engine/' "pytest engines/audio_engine/tests"
maybe_add '^hosts/advisor_host/' "pytest hosts/advisor_host/tests"
maybe_add '^shared/' "pytest shared/tests"
maybe_add '^tools/' "pytest tests/test_path_literals.py"

# Fallback if nothing matched
if [ "${#RUN_CMDS[@]}" -eq 0 ]; then
  RUN_CMDS=("make quick-check")
fi

echo "[affected] changed files:"
echo "${CHANGED:-(none)}"
echo "[affected] running:"
printf '  - %s\n' "${RUN_CMDS[@]}"

for cmd in "${RUN_CMDS[@]}"; do
  echo ">> ${cmd}"
  eval "${cmd}"
done
