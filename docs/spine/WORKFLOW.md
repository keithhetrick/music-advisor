# Spine Tier 1 Workflow (v1)

Concise map of how Tier 1 data flows through this repo. Use this to know where to start, what each script does, and how artifacts fit together.

ASCII flow (portable):

```ascii
[data/spine/spine_core_tracks_v1.csv]
          |
    (backfill scripts)
          v
 [data/spine/backfill/*.csv]
          |
[data/overrides/spine_audio_overrides_v1.csv]
          |
[tools/spine/spine_backfill_audio_v1.py]
          |
  +--------------------+
  | coverage/missing   |
  +--------------------+
          |
 [spine_master_v1.csv]
 [spine_master_v1_lanes.csv]
          |
   DB import (historical echo)
```

## Source + Core

- Canonical track list: `data/spine/spine_core_tracks_v1.csv` (40×40 ranks for 1985–2024).
- Lanes metadata: `data/spine/spine_master_v1.csv` and `data/spine/spine_master_v1_lanes.csv` (built from core).

## Backfill audio

- External candidates live under `data/external/` (audio-feature CSVs).
- Scan inventory: `python tools/spine/scan_external_datasets_v1.py` → writes `data/DATASET_AUDIO_CANDIDATES.md`.
- Backfill scripts (per source) emit CSVs under `data/spine/backfill/`:
  - Tonyrwen 1970–2020: `build_spine_audio_from_tonyrwen_v1.py`
  - Patrick 1960–2020: `build_spine_audio_from_patrick_v1.py`
  - Hot 100 lyrics+audio 2000–2023: `build_spine_audio_from_hot100_lyrics_audio_v1.py`
  - Hot100Songs (audio via charts): `build_spine_audio_from_hot100songs_v1.py`
  - Spotify 600k dump probe (coverage only): `build_spine_audio_from_yamaerenay_v1.py`

## Overrides

- Manual fixes: `data/overrides/spine_audio_overrides_v1.csv` (applied after backfills, before final merge).
- Keep provenance in Git; don’t hand-edit generated backfill outputs.

## Merge + reports

- Merge backfills + overrides: `python tools/spine/spine_backfill_audio_v1.py`
- Coverage: `python tools/spine/spine_coverage_report_v1.py`
- Missing audio: `python tools/spine/report_spine_missing_audio_v1.py`
- Prepare Spotify queries for remaining gaps: `python tools/spine/prepare_spotify_queries_for_missing_v1.py`

## Master builds

- Rebuild core/master (rare): `build_spine_master_v1.py`
- Build lanes: `build_spine_master_lanes_v1.py`
- Import to Historical Echo DB: `import_spine_into_historical_echo_db.py`
- Import lanes to DB: `import_spine_master_lanes_into_db_v1.py`

## Historical Echo probe

- Single-track search against Tier 1: `python tools/hci_echo_probe_from_spine_v1.py --features ... --top-k 10 --year-max 2020`

## Suggested sequences

- **Refresh + gap check:** `scan_external_datasets_v1.py` → `report_spine_missing_audio_v1.py`
- **Rebuild from scratch:** core → master → lanes → backfills → overrides → spine_backfill_audio_v1 → reports → DB import.

## Outputs to expect (checklist)

- Backfills under `data/spine/backfill/*.csv` (per source).
- Overrides file `data/overrides/spine_audio_overrides_v1.csv` applied post-backfill.
- Merged lane files: `spine_master_v1.csv`, `spine_master_v1_lanes.csv`.
- DB imports: lanes tables in `data/historical_echo/historical_echo.db` (Tier 1/2; Tier 3 planned).
- Reports: coverage/missing CSVs from `spine_coverage_report_v1.py` and `report_spine_missing_audio_v1.py`.
