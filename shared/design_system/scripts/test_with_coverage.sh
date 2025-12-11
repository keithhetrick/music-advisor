#!/usr/bin/env bash
set -euo pipefail

# Run from repo root or this script's directory.
cd "$(dirname "$0")/.."

swift test --enable-code-coverage

BINARY=".build/debug/MAStylePackageTests.xctest/Contents/MacOS/MAStylePackageTests"
PROFILE=".build/debug/codecov/default.profdata"
REPORT=".build/coverage.txt"

if [[ -f "$BINARY" && -f "$PROFILE" ]]; then
  xcrun llvm-cov report "$BINARY" -instr-profile="$PROFILE" > "$REPORT"
  echo "Coverage report written to $REPORT"
else
  echo "Coverage artifacts not found; ensure swift test --enable-code-coverage succeeded." >&2
  exit 1
fi
