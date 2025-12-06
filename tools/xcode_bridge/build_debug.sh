#!/usr/bin/env zsh
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"

# Ensure we use the full Xcode toolchain.
export DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
export CC="$(xcrun --find clang)"
export CXX="$(xcrun --find clang++)"
DERIVED="$SCRIPT_DIR/build/DerivedData"
mkdir -p "$DERIVED"
echo "IDEDerivedDataPath = $DERIVED" > "$SCRIPT_DIR/DerivedDataOverride.xcconfig"
export XCODE_XCCONFIG_FILE="$SCRIPT_DIR/DerivedDataOverride.xcconfig"
# Force a local HOME so any fallback DerivedData/logs land inside the project.
export HOME="$SCRIPT_DIR/build/home"
mkdir -p "$HOME"

cmake -S "$SCRIPT_DIR" -B "$SCRIPT_DIR/build" -G Xcode -DCMAKE_OSX_SYSROOT="$(xcrun --show-sdk-path)" \
      -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX"
# Keep DerivedData local to this folder for a fully self-contained bridge.
/usr/bin/xcodebuild \
  -project "$SCRIPT_DIR/build/XcodeBridgeDemo.xcodeproj" \
  -scheme "XcodeBridgeDemo" \
  -configuration Debug \
  -derivedDataPath "$SCRIPT_DIR/build/DerivedData" \
  build
