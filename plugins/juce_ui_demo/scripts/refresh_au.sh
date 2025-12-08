#!/usr/bin/env bash
set -euo pipefail

# Fast rebuild + install + register the AU for Logic/hosts.
# Usage: ./scripts/refresh_au.sh [Debug|Release]
# Requirements: a configured build folder (juce-universal preset).

CONFIG="${1:-Debug}"
PROJECT_ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
AU_PATH="$HOME/Library/Audio/Plug-Ins/Components/MAStyle JUCE Demo.component"

echo "Building (config=$CONFIG) with juce-universal preset..."
cmake --build "$BUILD_DIR" --config "$CONFIG"

echo "Installing AU/VST3 to user plugin folders..."
"$PROJECT_ROOT/scripts/install_root.sh" "$CONFIG"

echo "Registering AU with pluginkit..."
pluginkit -m -a "$AU_PATH"
killall -9 AudioComponentRegistrar 2>/dev/null || true

echo "Done. In Logic, open Plug-In Manager and 'Reset & Rescan Selection' for"
echo "MAStyle JUCE Demo if it doesn't appear immediately."
