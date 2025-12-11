#!/usr/bin/env bash
set -euo pipefail

# Simple lint: flag hard-coded /tmp paths in production sources.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

matches=$(grep -R "/tmp/" Sources \
  --include="*.swift" \
  --exclude-dir Tests \
  --exclude-dir .build \
  --exclude "*Test*" || true)

if [[ -n "${matches}" ]]; then
  echo "Found hard-coded /tmp paths in production sources:"
  echo "${matches}"
  exit 1
fi

echo "No /tmp usage detected in production sources."
