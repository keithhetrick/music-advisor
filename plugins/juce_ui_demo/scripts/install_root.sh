#!/usr/bin/env bash
set -euo pipefail

# Installs AU and VST3 into the standard user plugin folders (no vendor subfolder).
# Usage: ./scripts/install_root.sh [Debug|Release]
# Works with both single-config (Unix Makefiles) and multi-config generators.

CONFIG="${1:-Debug}"
PROJECT_ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"

AU_SRC_MULTI="$BUILD_DIR/$CONFIG/MAStyle JUCE Demo.component"
VST_SRC_MULTI="$BUILD_DIR/$CONFIG/MAStyle JUCE Demo.vst3"

AU_SRC_SINGLE="$BUILD_DIR/MAStyleJuceDemo_artefacts/AU/MAStyle JUCE Demo.component"
VST_SRC_SINGLE="$BUILD_DIR/MAStyleJuceDemo_artefacts/VST3/MAStyle JUCE Demo.vst3"

if [ -e "$AU_SRC_MULTI" ] && [ -e "$VST_SRC_MULTI" ]; then
  AU_SRC="$AU_SRC_MULTI"
  VST_SRC="$VST_SRC_MULTI"
else
  AU_SRC="$AU_SRC_SINGLE"
  VST_SRC="$VST_SRC_SINGLE"
fi

AU_DEST="$HOME/Library/Audio/Plug-Ins/Components/MAStyle JUCE Demo.component"
VST_DEST="$HOME/Library/Audio/Plug-Ins/VST3/MAStyle JUCE Demo.vst3"

echo "Installing to root plugin folders ($CONFIG)..."

if [ ! -e "$AU_SRC" ] || [ ! -e "$VST_SRC" ]; then
  echo "Built plugins not found. Build first:"
  echo "  # single-config (Unix Makefiles)"
  echo "  cmake --build $BUILD_DIR"
  echo "  # multi-config (Xcode/Visual Studio)"
  echo "  cmake --build $BUILD_DIR --config $CONFIG"
  exit 1
fi

# Remove stale installs to avoid nested bundles.
rm -rf "$AU_DEST" "$VST_DEST"

mkdir -p "$(dirname "$AU_DEST")" "$(dirname "$VST_DEST")"
rsync -a "$AU_SRC/" "$AU_DEST"
rsync -a "$VST_SRC/" "$VST_DEST"

echo "Installed AU  -> $AU_DEST"
echo "Installed VST3 -> $VST_DEST"
echo "Tip: clear AU cache if a host still doesn't see it:"
echo "  rm -f ~/Library/Caches/AudioUnitCache/*"
echo "  killall -9 AudioComponentRegistrar coreaudiod 2>/dev/null || true"
