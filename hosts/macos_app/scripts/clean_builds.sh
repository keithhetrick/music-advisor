#!/usr/bin/env zsh
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"

echo "Cleaning macOS app build artifacts at $BUILD_DIR"
rm -rf "$BUILD_DIR"
echo "Done."
