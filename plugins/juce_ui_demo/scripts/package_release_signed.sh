#!/usr/bin/env bash
set -euo pipefail

# Robust staging helper for Release artifacts.
# - Stages AU/VST3/Standalone into dist/
# - Optionally codesigns (if DEV_ID_APP is set)
# - Optionally notarizes/staples (if NOTARY_* vars are set)
#
# Usage:
#   ./scripts/package_release_signed.sh
# Environment (optional):
#   DEV_ID_APP="Developer ID Application: Your Name (TEAMID)"
#   NOTARY_APPLE_ID="your@appleid.com"
#   NOTARY_TEAM_ID="TEAMID"
#   NOTARY_APP_SPECIFIC_PW="xxxx-xxxx-xxxx-xxxx"   # App-specific password
#   KEYCHAIN_PROFILE="AC_PASSWORD"                 # If you use a keychain profile with notarytool

PROJECT_ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build/MAStyleJuceDemo_artefacts/Release"
OUT_DIR="$PROJECT_ROOT/dist"

AU_SRC="$BUILD_DIR/AU/MAStyle JUCE Demo.component"
VST3_SRC="$BUILD_DIR/VST3/MAStyle JUCE Demo.vst3"
APP_SRC="$BUILD_DIR/Standalone/MAStyle JUCE Demo.app"

mkdir -p "$OUT_DIR"

echo "Packaging unsigned artifacts to $OUT_DIR (Release)..."
rsync -a "$AU_SRC"  "$OUT_DIR/"
rsync -a "$VST3_SRC" "$OUT_DIR/"
rsync -a "$APP_SRC" "$OUT_DIR/"

if [ -n "${DEV_ID_APP:-}" ]; then
  echo "Codesigning with identity: $DEV_ID_APP"
  codesign --deep --force --options runtime --sign "$DEV_ID_APP" "$OUT_DIR/MAStyle JUCE Demo.component"
  codesign --deep --force --options runtime --sign "$DEV_ID_APP" "$OUT_DIR/MAStyle JUCE Demo.vst3"
  codesign --deep --force --options runtime --sign "$DEV_ID_APP" "$OUT_DIR/MAStyle JUCE Demo.app"
else
  echo "Skipping codesign (DEV_ID_APP not set)."
fi

ZIP_PATH="$OUT_DIR/MAStyleJUCE_Demo_Release.zip"
echo "Creating zip at $ZIP_PATH"
(cd "$OUT_DIR" && zip -r "$ZIP_PATH" "MAStyle JUCE Demo.component" "MAStyle JUCE Demo.vst3" "MAStyle JUCE Demo.app")

if [ -n "${NOTARY_APPLE_ID:-}" ] && [ -n "${NOTARY_TEAM_ID:-}" ] && [ -n "${NOTARY_APP_SPECIFIC_PW:-}" ]; then
  echo "Submitting for notarization..."
  xcrun notarytool submit "$ZIP_PATH" \
    --apple-id "$NOTARY_APPLE_ID" \
    --team-id "$NOTARY_TEAM_ID" \
    --password "$NOTARY_APP_SPECIFIC_PW" \
    --wait
  echo "Stapling tickets..."
  xcrun stapler staple "$OUT_DIR/MAStyle JUCE Demo.component"
  xcrun stapler staple "$OUT_DIR/MAStyle JUCE Demo.vst3"
  xcrun stapler staple "$OUT_DIR/MAStyle JUCE Demo.app"
else
  echo "Skipping notarization (NOTARY_* env vars not set)."
fi

echo "Done. Artifacts in $OUT_DIR"
