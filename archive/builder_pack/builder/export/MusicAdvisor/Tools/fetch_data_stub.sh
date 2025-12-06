#!/usr/bin/env bash
set -euo pipefail

# Stub fetch script: replace with your own storage URLs/bucket paths.
# Goal: keep heavy data out of the repo; fetch on demand into Data/.

DEST="Data"
MANIFEST="${DEST}/manifest.json"

if [[ ! -f "$MANIFEST" ]]; then
  echo "[ERR] $MANIFEST not found. Copy manifest.example.json to manifest.json and fill in remote URLs and checksums."
  exit 1
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "[ERR] Missing tool: $1" >&2; exit 1; }; }
need sha256sum || need shasum

hash_cmd="sha256sum"
command -v sha256sum >/dev/null 2>&1 || hash_cmd="shasum -a 256"

fetch_one() {
  local name="$1" url="$2" checksum="$3"
  local out="${DEST}/${name}"
  local out_dir
  out_dir="$(dirname "$out")"
  mkdir -p "$out_dir"

  echo "[INFO] Fetching ${name} ..."
  # Replace curl with your preferred fetcher (aws s3 cp, gsutil cp, etc.)
  curl -L "$url" -o "$out"

  echo "[INFO] Verifying checksum for ${name} ..."
  local got
  got="$($hash_cmd "$out" | awk '{print $1}')"
  if [[ "$got" != "$checksum" ]]; then
    echo "[ERR] Checksum mismatch for ${name}: expected ${checksum}, got ${got}" >&2
    exit 1
  fi
  echo "[OK] ${name} fetched and verified."
}

python - <<'PY' > /tmp/ma_fetch_list.json
import json, os
manifest = os.environ.get("MANIFEST")
data = json.load(open(manifest, "r"))
print(json.dumps(data.get("artifacts", [])))
PY

for row in $(jq -c '.[]' /tmp/ma_fetch_list.json); do
  name=$(echo "$row" | jq -r '.name')
  url=$(echo "$row" | jq -r '.remote')
  checksum=$(echo "$row" | jq -r '.checksum_sha256')
  if [[ -z "$name" || -z "$url" || -z "$checksum" ]]; then
    echo "[WARN] Skipping row with missing fields: $row"
    continue
  fi
  fetch_one "$name" "$url" "$checksum"
done

echo "[OK] All artifacts fetched."
