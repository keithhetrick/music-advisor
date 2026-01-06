#!/usr/bin/env bash
set -euo pipefail

threshold_mb=100
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
dist_dir="${repo_root}/dist"

if [[ ! -d "${dist_dir}" ]]; then
    echo "dist/ not found; size = 0 MB (OK)"
    exit 0
fi

size_mb=$(du -sm "${dist_dir}" | awk '{print $1}')
echo "dist size: ${size_mb} MB (threshold ${threshold_mb} MB)"

if (( size_mb > threshold_mb )); then
    echo "WARNING: dist exceeds ${threshold_mb} MB. Consider pruning old archives or tightening packaging." >&2
    exit 1
fi
