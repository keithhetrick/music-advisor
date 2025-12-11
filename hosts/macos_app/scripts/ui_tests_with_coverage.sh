#!/usr/bin/env bash
set -euo pipefail

# Run from repo root or this script's directory.
cd "$(dirname "$0")/.."

SCHEME="MusicAdvisorMacApp-UI"
PROJECT="MusicAdvisorMacApp.xcodeproj"
ARCH="$(uname -m)"
DESTINATION="platform=macOS,arch=${ARCH}"
DERIVED_DATA="$PWD/build/ui-tests-derived"
REPORT_DIR="$PWD/build"
TEXT_REPORT="$REPORT_DIR/ui-test-coverage.txt"
JSON_REPORT="$REPORT_DIR/ui-test-coverage.json"
XCRESULT_ZIP="$REPORT_DIR/ui-tests-latest.xcresult.zip"

mkdir -p "$DERIVED_DATA" "$REPORT_DIR"

xcodebuild \
  -scheme "$SCHEME" \
  -project "$PROJECT" \
  -destination "$DESTINATION" \
  -enableCodeCoverage YES \
  -derivedDataPath "$DERIVED_DATA" \
  test

XCRESULT=$(ls -1dt "$DERIVED_DATA/Logs/Test"/*.xcresult | head -n 1)
if [[ -z "$XCRESULT" ]]; then
  echo "No xcresult found in $DERIVED_DATA/Logs/Test" >&2
  exit 1
fi

set +e
xcrun xccov view --report "$XCRESULT" > "$TEXT_REPORT"
if [[ $? -ne 0 ]]; then
  echo "Warning: xccov text report failed; coverage output not generated" >&2
fi
xcrun xccov view --report --json "$XCRESULT" > "$JSON_REPORT"
if [[ $? -ne 0 ]]; then
  echo "Warning: xccov JSON report failed; coverage output not generated" >&2
fi
set -e

# Archive xcresult for CI consumption
rm -f "$XCRESULT_ZIP"
/usr/bin/zip -qry "$XCRESULT_ZIP" "$XCRESULT"

echo "UI test coverage written to:"
echo "  $TEXT_REPORT"
echo "  $JSON_REPORT"
echo "XCResult archive: $XCRESULT_ZIP"
