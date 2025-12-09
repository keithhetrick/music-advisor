#!/usr/bin/env zsh
# Build a release .app bundle (SwiftPM) and zip it for sharing.
# No signing/notarization; this is for internal/dev distribution.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname "$0")/.." && pwd)"
SCRATCH="$PROJECT_DIR/build/.swiftpm-release"
LOCAL_HOME="$PROJECT_DIR/build/home-release"
MODULE_CACHE="$SCRATCH/ModuleCache"
ARCH="$(uname -m)"
TRIPLE="${ARCH}-apple-macosx"
CONFIG="release"
BINARY_NAME="MusicAdvisorMacApp"
BINARY_PATH="$SCRATCH/$TRIPLE/$CONFIG/$BINARY_NAME"
BUNDLE_ROOT="$PROJECT_DIR/dist/${BINARY_NAME}.app"
ZIP_PATH="$PROJECT_DIR/dist/${BINARY_NAME}.zip"

mkdir -p "$SCRATCH" "$LOCAL_HOME" "$MODULE_CACHE" "$PROJECT_DIR/dist"

echo "Building $BINARY_NAME for $TRIPLE ($CONFIG)..."
cd "$PROJECT_DIR"
HOME="$LOCAL_HOME" \
SWIFT_MODULE_CACHE_PATH="$MODULE_CACHE" \
LLVM_MODULE_CACHE_PATH="$MODULE_CACHE" \
SWIFTPM_DISABLE_SANDBOX=1 \
swift build --scratch-path "$SCRATCH" --configuration "$CONFIG" --disable-sandbox

if [[ ! -x "$BINARY_PATH" ]]; then
  echo "ERROR: did not find built binary at $BINARY_PATH"
  echo "Existing binaries:"
  find "$SCRATCH" -name "$BINARY_NAME" -type f -maxdepth 4 -print 2>/dev/null || true
  exit 1
fi

echo "Assembling .app bundle at $BUNDLE_ROOT"
rm -rf "$BUNDLE_ROOT"
mkdir -p "$BUNDLE_ROOT/Contents/MacOS" "$BUNDLE_ROOT/Contents/Resources"

cat > "$BUNDLE_ROOT/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key> <string>MusicAdvisorMacApp</string>
    <key>CFBundleDisplayName</key> <string>Music Advisor</string>
  <key>CFBundleIdentifier</key> <string>com.bellweatherstudios.musicadvisor.host</string>
    <key>CFBundleExecutable</key> <string>MusicAdvisorMacApp</string>
    <key>CFBundlePackageType</key> <string>APPL</string>
    <key>CFBundleShortVersionString</key> <string>0.1.0</string>
    <key>CFBundleVersion</key> <string>1</string>
    <key>LSMinimumSystemVersion</key> <string>12.0</string>
    <key>NSHighResolutionCapable</key> <true/>
</dict>
</plist>
EOF

cp "$BINARY_PATH" "$BUNDLE_ROOT/Contents/MacOS/$BINARY_NAME"

echo "Creating zip -> $ZIP_PATH"
rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$BUNDLE_ROOT" "$ZIP_PATH"

echo "Done."
echo "  Bundle: $BUNDLE_ROOT"
echo "  Zip:    $ZIP_PATH"
