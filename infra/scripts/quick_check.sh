#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
# Silence known third-party deprecation noise during CI/local runs
export PYTHONWARNINGS="ignore::DeprecationWarning:audioread.*,ignore::DeprecationWarning:librosa.*,ignore::FutureWarning:librosa.*"
./infra/scripts/with_repo_env.sh -m tools.ma_tasks test-affected "$@"
