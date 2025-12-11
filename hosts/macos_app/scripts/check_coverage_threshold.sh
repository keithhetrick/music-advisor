#!/usr/bin/env bash
set -euo pipefail

# Fail if the aggregate coverage in coverage.txt is below MIN_COVERAGE (integer percent).
# Looks in build/coverage-latest/coverage.txt first, then .build/coverage.txt.

MIN_COVERAGE="${MIN_COVERAGE:-}"
if [[ -z "${MIN_COVERAGE}" ]]; then
  echo "MIN_COVERAGE not set; skipping threshold check."
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

src=""
for candidate in build/coverage-latest/coverage.txt .build/coverage.txt; do
  if [[ -f "$candidate" ]]; then
    src="$candidate"
    break
  fi
done

if [[ -z "${src}" ]]; then
  echo "No coverage.txt found; cannot enforce threshold ${MIN_COVERAGE}%."
  exit 1
fi

cov=$(perl -ne 'if (/([0-9]+(?:\.[0-9]+)?)%/) { print $1; exit 0 }' "$src" || true)
if [[ -z "${cov}" ]]; then
  echo "Could not parse coverage percentage from ${src}"
  exit 1
fi

cov_int=${cov%.*}
echo "Parsed coverage: ${cov}% from ${src}; required >= ${MIN_COVERAGE}%"

if (( cov_int < MIN_COVERAGE )); then
  echo "Coverage ${cov_int}% is below threshold ${MIN_COVERAGE}%"
  exit 1
fi

echo "Coverage threshold met."
