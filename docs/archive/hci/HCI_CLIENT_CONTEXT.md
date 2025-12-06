# HCI + Echo Context (Client Rich)

Inject historical echo + HCI context into `.client.rich.txt` with `ma_add_echo_to_client_rich_v1.py`.

## Command

````bash
python tools/hci/ma_add_echo_to_client_rich_v1.py \
  --root features_output/2025/11/25/Some Track \
  --skip-existing \
  --verbose
```text

- Defaults: all tiers (tier1_modern,tier2_modern,tier3_modern) with dedupe priority tier1 > tier2 > tier3 (same song appears once).
- `--skip-existing`: skip files that already have `historical_echo_v1`.
- `--verbose`: per-file logging; rewrites only if content changes.

## Header Structure (inserted at top)

```text
# ==== MUSIC ADVISOR - SONG CONTEXT ====
# Author: Keith Hetrick - injects HCI+Echo context into .client.rich.txt
# Version: HCI+Echo context v1.1
# Generated: <UTC timestamp>

# STRUCTURE_POLICY: mode=optional | reliable=false | use_ttc=false | use_exposures=false
# GOLDILOCKS_POLICY: active=true | priors={'Market': 0.5, 'Emotional': 0.5} | caps={'Market': 0.58, 'Emotional': 0.58}
# HCI_POLICY: HCI_v1_final_score is canonical; raw/calibrated are provided for transparency only.
# CONTEXT: region=US, profile=Pop, audio_name=UNKNOWN_AUDIO
# HCI_V1_SUMMARY: final=<score> | role=<role> | raw=<raw> | calibrated=<calibrated>
# ==== HCI INTERPRETATION ====
#   interpretation: ...
#   notes: ...
# AUDIO_PIPELINE:
#   normalized_for_features=<true/false>
#   gain_db=<gain applied>
#   loudness_raw_LUFS=<raw LUFS>
#   loudness_norm_LUFS=<normalized LUFS>
#   qa_peak_dbfs=<peak>
#   qa_rms_dbfs=<rms>
#   qa_clipping=<true/false>
#   qa_silence_ratio=<ratio>
# ==== HISTORICAL ECHO V1 ====
# ECHO SUMMARY: tiers=... | primary_decade=... | closest=...
# NEIGHBORS...
````

## Behavior

- Uses sibling `.features.json` + `.hci.json` to build context.
- Tier dedupe prevents duplicate songs across tiers (prefers Tier 1).
- Neighbor header shows up to 4 per tier; JSON includes full neighbor list (top_k).

## Tips

- For Tier 1 only: pass `--tiers tier1_modern`.
- For faster runs: lower `--top-k` or use `--skip-existing`.
