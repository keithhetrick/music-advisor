ma-validate CLI

Validate a MusicAdvisor DATA_PACK JSON.

Usage:
  python ma_validate.py pack.json --schema datapack.schema.json --strict
  python ma_validate.py pack.json --schema datapack.schema.json --strict --autofix --out patched.json

Autofixes:
  - Replace en/em dashes in tempo_band_bpm.
  - Create MVP block if missing.
  - Add Baseline skeleton if missing.
  - Ensure Known_Gaps array.

Exit codes:
  0 valid, 1 errors, 2 IO/runtime problems.
