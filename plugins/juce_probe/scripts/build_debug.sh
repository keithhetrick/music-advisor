#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cmake -S "${PROJECT_ROOT}" -B "${PROJECT_ROOT}/build" -G Xcode
cmake --build "${PROJECT_ROOT}/build" --config Debug
