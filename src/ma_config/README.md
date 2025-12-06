# ma_config

Centralized configuration helpers for paths, profiles, and shared constants. This package keeps pipelines and wrappers data-driven by pulling defaults from the repo and allowing opt-in overrides via environment variables or small config files.

## Modules

- `paths.py`: resolves repo/data/calibration roots and common artifact locations (features output, lyric Intel DB, historical echo DB). Every path supports env overrides (e.g., `MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`).
- `pipeline.py`: defaults for pipeline driver profiles/timeouts (`HCI_BUILDER_PROFILE_DEFAULT`, `NEIGHBORS_PROFILE_DEFAULT`, `SIDECAR_TIMEOUT_DEFAULT`), intended to be overridden by env or driver JSON config.
- `profiles.py`: lyric/TTC profile resolution helpers and default config paths. Precedence: CLI args > env vars > JSON config fields > defaults, so callers can override without code edits.
- `constants.py`: shared enums/lists for era buckets, LCI axes, tier thresholds.
- `neighbors.py`: neighbor-related defaults and profile helpers.
- `scripts.py`: utilities for script-level configuration.

## Env overrides (paths.py highlights)

| Path helper                       | Default location                          | Env override                |
| --------------------------------- | ----------------------------------------- | --------------------------- |
| `get_data_root()`                 | `<repo>/data`                             | `MA_DATA_ROOT`              |
| `get_calibration_root()`          | `<repo>/calibration`                      | `MA_CALIBRATION_ROOT`       |
| `get_external_data_root()`        | `<data_root>/external`                    | `MA_EXTERNAL_DATA_ROOT`     |
| `get_features_output_root()`      | `<data_root>/features_output`             | — (inherits `MA_DATA_ROOT`) |
| `get_lyric_intel_db_path()`       | `<data_root>/lyric_intel/lyric_intel.db`  | —                           |
| `get_historical_echo_db_path()`   | `<data_root>/historical_echo/historical_echo.db` | —                     |
| `get_kaggle_year_end_lyrics_path()` | `<external>/year_end/year_end_hot_100_lyrics_kaylin_1965_2015.csv` | `MA_KAGGLE_YEAR_END_LYRICS` |
| `get_hot100_lyrics_audio_path()`  | `<external>/lyrics/hot_100_lyrics_audio_2000_2023.csv` | `MA_HOT100_LYRICS_AUDIO`   |
| `get_core_1600_csv_path()`        | `<data_root>/core_1600_with_spotify_patched.csv` | `MA_CORE1600_CSV`        |
| `get_spine_root()`                | `<data_root>/spine`                       | `MA_SPINE_ROOT`             |
| `get_spine_backfill_root()`       | `<spine_root>/backfill`                   | `MA_SPINE_BACKFILL_ROOT`    |
| `get_spine_master_csv()`          | `<data_root>/spine/spine_master.csv`      | `MA_SPINE_MASTER`           |

## Usage patterns

- Prefer these helpers over hard-coded paths in scripts/tools; tests rely on importability and env-driven behavior.
- For pipeline driver settings, use `ma_config.pipeline` defaults and allow env/JSON overrides rather than embedding literals.
- Keep new config knobs small and centralized here so Automator/CLI/CI can override without code edits.
- When adding a new profile/config override, mirror it in docs (`docs/config_and_paths.md`) and note precedence to avoid ambiguity.
- For debugging pipeline behavior, see `docs/DEBUGGING.md` and `docs/pipeline/PIPELINE_DRIVER.md`.
