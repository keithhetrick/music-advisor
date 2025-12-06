#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-data/features_output/$(date +%Y/%m/%d)}"
CALIB="${AUDIO_HCI_CALIBRATION:-shared/calibration/hci_calibration_us_pop_v1.json}"
MARKET="${AUDIO_MARKET_NORMS:-shared/calibration/market_norms_us_pop.json}"

echo "[HCI_BATCH] Root: $ROOT"

# 1) Recompute axes + raw HCI for every .features.json
find "$ROOT" -type f -name '*.features.json' | while read -r f; do
  base="${f%.features.json}"
  out="${base}.hci.json"
  echo "[HCI_BATCH] hci_axes -> $out"
  python tools/hci_axes.py \
    --features-full "$f" \
    --market-norms "$MARKET" \
    --out "$out"
done

# 2) Apply calibration once to the whole root
echo "[HCI_BATCH] Applying calibration from $CALIB"
python tools/hci_calibration.py apply \
  --root "$ROOT" \
  --calib "$CALIB"
