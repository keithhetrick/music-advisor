#!/usr/bin/env bash
set -euo pipefail

# Installs AU and VST3 builds into user plugin folders under a nested vendor folder.
# Usage: ./scripts/install_plugins.sh [Debug|Release]

CONFIG="${1:-Debug}"
PROJECT_ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"

# Support both multi-config (Xcode/MSVC) and single-config (Unix Makefiles) builds.
AU_SRC_MULTI="$BUILD_DIR/$CONFIG/MAStyle JUCE Demo.component"
VST_SRC_MULTI="$BUILD_DIR/$CONFIG/MAStyle JUCE Demo.vst3"

AU_SRC_SINGLE="$BUILD_DIR/MAStyleJuceDemo_artefacts/AU/MAStyle JUCE Demo.component"
VST_SRC_SINGLE="$BUILD_DIR/MAStyleJuceDemo_artefacts/VST3/MAStyle JUCE Demo.vst3"

AU_SRC=""
VST_SRC=""

if [ -e "$AU_SRC_MULTI" ] && [ -e "$VST_SRC_MULTI" ]; then
  AU_SRC="$AU_SRC_MULTI"
  VST_SRC="$VST_SRC_MULTI"
else
  AU_SRC="$AU_SRC_SINGLE"
  VST_SRC="$VST_SRC_SINGLE"
fi

AU_DEST="$HOME/Library/Audio/Plug-Ins/Components/Bellweather Studios/MAStyle JUCE Demo.component"
VST_DEST="$HOME/Library/Audio/Plug-Ins/VST3/Bellweather Studios/MAStyle JUCE Demo.vst3"

echo "Installing ($CONFIG)..."

if [ ! -e "$AU_SRC" ] || [ ! -e "$VST_SRC" ]; then
  echo "Built plugins not found. Build first:"
  echo "  # single-config (Unix Makefiles)"
  echo "  cmake --build $BUILD_DIR"
  echo "  # multi-config (Xcode/Visual Studio)"
  echo "  cmake --build $BUILD_DIR --config $CONFIG"
  exit 1
fi

mkdir -p "$(dirname "$AU_DEST")" "$(dirname "$VST_DEST")"
# Ensure we don't end up with nested bundles if a stale target exists.
rm -rf "$AU_DEST" "$VST_DEST"
rsync -a "$AU_SRC/" "$AU_DEST"
rsync -a "$VST_SRC/" "$VST_DEST"

echo "Installed AU -> $AU_DEST"
echo "Installed VST3 -> $VST_DEST"
