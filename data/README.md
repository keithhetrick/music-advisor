# data/ layout

This folder is kept in the repo (with this README) but its contents are git-ignored by default. It is split into:

- `data/public/`

  - Shareable/bootstrap assets (e.g., spine, market_norms, lyric_intel if provided).
  - Populated via the manifest-driven bootstrap:

    ```bash
    python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json
    ```

- `data/private/local_assets/`
  - Local-only datasets and models (HCI v2 targets/training, core_1600 CSVs, historical_echo.db, etc.).
  - Subfolders include `hci_v2/`, `core_spine/`, `audio_models/`, `yearend_hot100/`, `external/`, `docs/`, etc.
- `data/private/scratch|experiments|heavy_internal/`
  - Your own scratch/experimental data. Never fetched, never uploaded.
- `data/features_output/`
  - Generated outputs produced by runs; safe to delete/rebuild.

Private inventory (local_assets) overview:

- `hci_v2/`: targets/corpus/training/eval/overlap seeds.
- `core_spine/`: core_1600 CSVs, overrides, unmatched reports.
- `historical_echo/`: historical_echo.db and related artifacts.
- `audio_models/`: trained joblib/meta/calibration for audio/HCI v2.
- `yearend_hot100/`: derived year-end aggregates.
- `external/`: source datasets (weekly/year_end/lyrics/etc.).
- `lyric_intel/`: lyric DBs/backups/samples (keep private by default).
- `docs/`: local dataset inventories.

You can override the data root with:

```bash
export MA_DATA_ROOT=/path/to/custom/data
```

All path helpers resolve relative to MA_DATA_ROOT. Calibration ships in `shared/calibration/` and is not fetched from S3.
