# Spine + TTC Quickstart

Fast path to build spine lanes/backfills and add TTC annotations. Use this to answer “what do I run” without digging through multiple docs.

## Spine (Tier 1) — minimal workflow

```bash
# Scan external datasets
python tools/spine/scan_external_datasets_v1.py

# Run backfills (pick relevant sources)
python tools/spine/build_spine_audio_from_tonyrwen_v1.py
python tools/spine/build_spine_audio_from_patrick_v1.py
# ...other backfills under tools/spine/ (see BACKFILLS.md)

# Apply overrides + merge
python tools/spine/spine_backfill_audio_v1.py

# Reports
python tools/spine/spine_coverage_report_v1.py
python tools/spine/report_spine_missing_audio_v1.py
```

Outputs to expect:

- `data/spine/backfill/*.csv` backfills
- `data/overrides/spine_audio_overrides_v1.csv` applied
- `spine_master_v1.csv` / `spine_master_v1_lanes.csv`
- Coverage/missing reports under `data/spine/`
- Lanes imported into `data/historical_echo/historical_echo.db` (Tier 1/2)

More details: `docs/spine/WORKFLOW.md`, lane columns in `docs/spine/README.md`.

## TTC — add chorus timing sidecar

1. Create TTC table/CSV/JSONL (schema: `docs/schemas/ttc_annotations.schema.json`). Populate fields:
   - `slug`, `ttc_first_chorus_sec` (required), optional beats/bars/runtime/ratio/confidence/source/method/notes.
2. Wire extractors to read TTC by `slug` and emit the `TTC` block in `*.features.json`.
3. Surface TTC in packs/client.rich when present (`STRUCTURE_POLICY.use_ttc=true`).

Example JSONL row:

```json
{
  "slug": "artist__title",
  "ttc_first_chorus_sec": 42.7,
  "ttc_confidence": 0.78,
  "ttc_source": "harmonix",
  "ttc_method": "ttc_rule_based_v1",
  "notes": "verified in DAW"
}
```

Schema: `docs/schemas/ttc_annotations.schema.json`; plan details: `docs/ttc/TTC_PLAN_v1.md`.
