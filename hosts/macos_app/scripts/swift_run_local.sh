#!/usr/bin/env zsh
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname "$0")/.." && pwd)"
SCRATCH="$PROJECT_DIR/build/.swiftpm"
LOCAL_HOME="$PROJECT_DIR/build/home"
MODULE_CACHE="$SCRATCH/ModuleCache"

mkdir -p "$LOCAL_HOME" "$SCRATCH" "$MODULE_CACHE"

echo "Using PROJECT_DIR=$PROJECT_DIR"
echo "Using HOME=$LOCAL_HOME"
echo "Using scratch path=$SCRATCH"
echo "Using module cache=$MODULE_CACHE"

cd "$PROJECT_DIR"

HOME="$LOCAL_HOME" \
SWIFT_MODULE_CACHE_PATH="$MODULE_CACHE" \
LLVM_MODULE_CACHE_PATH="$MODULE_CACHE" \
SWIFTPM_DISABLE_SANDBOX=1 \
swift build --scratch-path "$SCRATCH" --disable-sandbox

# Package the SwiftPM executable into a lightweight .app so macOS will focus it.
BIN_PATH=$(swift build --show-bin-path --scratch-path "$SCRATCH" --disable-sandbox)
if [[ -z "$BIN_PATH" || ! -x "$BIN_PATH/MusicAdvisorMacApp" ]]; then
  echo "Could not find MusicAdvisorMacApp binary under $BIN_PATH"
  exit 1
fi

APP_BUNDLE="$PROJECT_DIR/build/.swiftpm/MusicAdvisorMacApp.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
mkdir -p "$APP_MACOS"

# Minimal Info.plist so macOS treats this as a bundle (helps focus/activation).
cat > "$APP_CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>MusicAdvisorMacApp</string>
  <key>CFBundleDisplayName</key><string>Music Advisor</string>
  <key>CFBundleExecutable</key><string>MusicAdvisorMacApp</string>
  <key>CFBundleIdentifier</key><string>com.bellweatherstudios.macosapp</string>
  <key>CFBundleVersion</key><string>0.1.0</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict>
</plist>
PLIST

cp "$BIN_PATH/MusicAdvisorMacApp" "$APP_MACOS/MusicAdvisorMacApp"
chmod +x "$APP_MACOS/MusicAdvisorMacApp"

echo "Opening $APP_BUNDLE"
if ! open "$APP_BUNDLE" 2>/dev/null; then
  echo "open failed (possibly headless shell); running the binary directly..."
  "$APP_MACOS/MusicAdvisorMacApp" &
fi
