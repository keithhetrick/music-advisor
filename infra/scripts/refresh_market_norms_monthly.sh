#!/usr/bin/env bash
# Monthly norms refresh (playlist-based)
# Usage: set PLAYLISTS (comma IDs), REGION, TIER, VERSION (e.g., 2025-01).
set -euo pipefail

PLAYLISTS="${PLAYLISTS:-37i9dQZEVXbLRQDuF5jeBp}" # default: US Top 50
REGION="${REGION:-US}"
TIER="${TIER:-StreamingTop200}"
VERSION="${VERSION:-$(date +%Y-%m)}"
RAW_CSV="/tmp/market_norms_${REGION}_${TIER}_${VERSION}_raw.csv"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -z "${SPOTIFY_CLIENT_ID:-}" ] || [ -z "${SPOTIFY_CLIENT_SECRET:-}" ]; then
  echo "[ERR] SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in env." >&2
  exit 1
fi

echo "[INFO] Fetching playlists -> $RAW_CSV"
python scripts/fetch_spotify_playlist_features.py --playlists "$PLAYLISTS" --out "$RAW_CSV" --access-token "${SPOTIFY_ACCESS_TOKEN:-}"

echo "[INFO] Building snapshot version $VERSION region=$REGION tier=$TIER"
python scripts/build_market_norms_snapshot.py --csv "$RAW_CSV" --region "$REGION" --tier "$TIER" --version "$VERSION" --out data/market_norms

echo "[DONE] Snapshot ready under data/market_norms/${REGION}_${TIER}_${VERSION}.json"
