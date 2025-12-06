# Data Bootstrap & Layout

This repo keeps `data/` empty by default (git-ignored). To run with real assets, you must populate it. Two options:

1. **Download from your own S3/HTTPS bucket** using the bootstrap script.
2. **Use your own local copies** and point env vars to them.

## Bootstrap via manifest

- Manifest: `infra/scripts/data_manifest.json` (fill real URLs + SHA256 checksums). Dest paths point to `data/public/...` to keep shareable assets separate from private/local-only data.
- Script: `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`
- Example manifest entry:
  ```json
  {
    "name": "market_norms_us_pop",
    "url": "https://s3.amazonaws.com/your-bucket/market_norms_us_pop.json",
    "sha256": "fill_me",
    "dest": "data/public/market_norms/market_norms_us_pop.json",
    "optional": false
  }
  ```
- Optional entries (e.g., `lyric_intel.db`) can be marked `"optional": true`; failures won’t stop the script.
- The script verifies checksums when provided. Use HTTPS/S3 presigned or public URLs; keep creds out of the repo.

## Data layout (current)

```
data/
  public/           # shareable/bootstrap assets fetched from S3/HTTPS (manifest allowlist)
    market_norms/
    spine/
    lyric_intel/    # optional
  private/
    local_assets/   # local-only datasets/models (HCI v2 targets/training, core_1600, historical_echo.db, etc.)
    scratch/ experiments/ heavy_internal/  # your personal scratch; never uploaded
  features_output/  # pipeline outputs (generated per run)
```

Private/local_assets quick inventory:

- `hci_v2/` — targets/corpus/training/eval/overlap seeds
- `core_spine/` — core_1600 CSVs, overrides, unmatched
- `historical_echo/` — historical_echo.db and related outputs
- `audio_models/` — trained joblib/meta/calibration for audio/HCI v2
- `yearend_hot100/` — derived year-end aggregates
- `external/` — source datasets (weekly/year_end/lyrics/etc.)
- `lyric_intel/` — lyric DBs/backups/samples (keep private by default)
- `docs/` — local dataset inventories

Current `data/public/` inventory (expected in manifest):

- `market_norms/market_norms_us_pop.json`
- `spine/spine_master.csv`
- `lyric_intel/lyric_intel.db` (optional; only if cleared for distribution)

Lyric Intel DBs default to `data/private/local_assets/lyric_intel/` (kept local). Only add to manifest/S3 if fully cleared.

## Calibration

- Included in repo under `shared/calibration/`. No download required. `MA_CALIBRATION_ROOT` defaults here.

## Path helpers & env overrides

Use `shared.config.paths` (re-exported via `shared.utils.paths`) instead of hard-coded paths. Env overrides:

- `MA_DATA_ROOT` (default: `<repo>/data`)
- `MA_CALIBRATION_ROOT` (default: `<repo>/shared/calibration`)
- `MA_EXTERNAL_DATA_ROOT`, `MA_SPINE_ROOT`, `MA_SPINE_MASTER`, etc.

Override example:

```
export MA_DATA_ROOT=/custom/path
python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json
```

## Footprint considerations

- Data is downloaded locally when you run the bootstrap script; nothing is committed.
- If you want zero local DB footprint, you would need to serve datasets via an API and adapt code to stream; current pipelines expect local files under `MA_DATA_ROOT`.

## Quick start

1. Fill `infra/scripts/data_manifest.json` with real URLs/checksums.
2. Run `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`.
3. Run `make e2e-app-smoke` or `make quick-check`.

To publish/update public assets to S3 (shareable only):

```
BUCKET=music-advisor-data-external-database-resources PREFIX=v1/data/public infra/scripts/data_sync_public.sh
```

This syncs only `data/public/` to the configured bucket/prefix (no delete by default).
