#!/usr/bin/env zsh
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname "$0")/.." && pwd)"
SCRATCH="$PROJECT_DIR/build/.swiftpm"
LOCAL_HOME="$PROJECT_DIR/build/home"

mkdir -p "$LOCAL_HOME" "$SCRATCH"

echo "Using PROJECT_DIR=$PROJECT_DIR"
echo "Using HOME=$LOCAL_HOME"
echo "Using scratch path=$SCRATCH"

cd "$PROJECT_DIR"

HOME="$LOCAL_HOME" swift build --scratch-path "$SCRATCH"
HOME="$LOCAL_HOME" swift run   --scratch-path "$SCRATCH"
