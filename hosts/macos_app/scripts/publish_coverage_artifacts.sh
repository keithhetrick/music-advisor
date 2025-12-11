#!/usr/bin/env bash
set -euo pipefail

# Consolidate macOS app coverage artifacts into build/coverage-latest for CI publishing.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEST="build/coverage-latest"
rm -rf "$DEST"
mkdir -p "$DEST"

copy_if_exists() {
  local src="$1"
  if [[ -f "$src" ]]; then
    cp "$src" "$DEST"/
    echo "Copied $(basename "$src")"
  fi
}

copy_if_exists ".build/coverage.txt"
copy_if_exists ".build/coverage.json"
copy_if_exists "build/ui-test-coverage.txt"
copy_if_exists "build/ui-test-coverage.json"

# Copy latest xcresult if present
latest_xcresult=$(ls -1 build/ui-tests-derived/Logs/Test/*.xcresult 2>/dev/null | sort | tail -n 1 || true)
if [[ -n "${latest_xcresult}" && -e "${latest_xcresult}" ]]; then
  zip_name="$DEST/ui-tests-latest.xcresult.zip"
  /usr/bin/zip -qry "$zip_name" "$latest_xcresult" || true
  if [[ -f "$zip_name" ]]; then
    echo "Zipped xcresult to $zip_name"
  else
    echo "xcresult zip skipped (zip failed or no attachments)"
  fi
else
  echo "No xcresult found; skipping xcresult bundle."
fi

echo "Coverage artifacts collected in $DEST"
