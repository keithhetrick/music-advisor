#!/bin/zsh
set -u  # no -e so one failure doesn't kill the loop

REPO="${REPO:-$HOME/music-advisor}"
cd "$REPO"

if [[ -x "$REPO/.venv/bin/python" ]]; then
  PY="$REPO/.venv/bin/python"
else
  PY="python3"
fi

# Narrow to your calibration batch for now:
TRACK_ROOT="features_output/2025/11/14/Calibration_Songs_2025Q4"

processed=0
skipped_no_payload=0

echo "Scanning for features.json under: $TRACK_ROOT"
count_feats=$(find "$TRACK_ROOT" -type f -name '*.features.json' | wc -l | tr -d ' ')
echo "Found $count_feats features.json files"
echo ""

find "$TRACK_ROOT" -type f -name '*.features.json' -print0 | \
while IFS= read -r -d '' FEATURES_JSON; do
  track_dir="$(dirname "$FEATURES_JSON")"
  STEM="$(basename "$track_dir")"

  CLIENT_JSON="$track_dir/$STEM.client.json"
  HCI_JSON="$track_dir/$STEM.hci.json"
  CLIENT_RICH="$track_dir/$STEM.client.rich.txt"

  INPUT_JSON=""
  OUTPUT_RICH=""
  if [[ -f "$CLIENT_JSON" ]]; then
    INPUT_JSON="$CLIENT_JSON"
    OUTPUT_RICH="$CLIENT_RICH"
  else
    echo "Skipping (no client json): $track_dir"
    ((skipped_no_payload++))
    continue
  fi

  echo "== $STEM =="

  "$PY" tools/ma_simple_hci_from_features.py \
    --features "$FEATURES_JSON" \
    --out      "$HCI_JSON"

  "$PY" tools/ma_merge_client_and_hci.py \
    --client-json "$INPUT_JSON" \
    --hci      "$HCI_JSON" \
    --out      "$OUTPUT_RICH" \
    --client-out "$OUTPUT_RICH"

  echo "  -> $OUTPUT_RICH"
  ((processed++))
done

echo ""
echo "Bulk HCI run complete."
echo "  Processed tracks : $processed"
echo "  Skipped (no payload) : $skipped_no_payload"
