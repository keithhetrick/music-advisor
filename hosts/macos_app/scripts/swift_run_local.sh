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

HOME="$LOCAL_HOME" \
SWIFT_MODULE_CACHE_PATH="$MODULE_CACHE" \
LLVM_MODULE_CACHE_PATH="$MODULE_CACHE" \
SWIFTPM_DISABLE_SANDBOX=1 \
swift run   --scratch-path "$SCRATCH" --disable-sandbox
