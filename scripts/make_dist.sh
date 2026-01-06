#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/make_dist.sh [--name NAME] [--dirty-ok]

Creates dist/<name>.zip from HEAD tracked files via git archive (small, reproducible).
Refuses to run on a dirty git tree unless --dirty-ok is set (uncommitted files are not included).

Options:
  --name NAME   Override archive base name (default: music-advisor-YYYYMMDD)
  --dirty-ok    Allow running with uncommitted changes (still only HEAD files will be packaged)
  -h, --help    Show this help
EOF
}

ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NAME_DEFAULT="music-advisor-$(date +%Y%m%d)"
ARCHIVE_NAME="$NAME_DEFAULT"
DIRTY_OK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      ARCHIVE_NAME="$2"
      shift 2
      ;;
    --dirty-ok)
      DIRTY_OK=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ $DIRTY_OK -ne 1 ]]; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Refusing to run: git tree is dirty (use --dirty-ok to override; only committed files are archived)" >&2
    exit 2
  fi
fi

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"
ARCHIVE_PATH="$OUTDIR/$ARCHIVE_NAME.zip"

echo "Building archive at $ARCHIVE_PATH"

# Package only tracked files at HEAD for maximum reproducibility and small size.
git archive --format zip --output "$ARCHIVE_PATH" HEAD

echo "Archive ready: $ARCHIVE_PATH"
