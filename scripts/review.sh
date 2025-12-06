#!/usr/bin/env bash
set -euo pipefail

# Codex review entrypoint: runs the helper's git/verify gate and affected plan.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python -m ma_helper github-check --require-clean --preflight --verify --ci-plan --base origin/main
