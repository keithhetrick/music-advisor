#!/usr/bin/env bash
set -euo pipefail

# Build and run using the current user's HOME (no overrides).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_DIR}"
swift build
swift run
