# Config and Paths (env-aware)

Shared locator: `ma_config` (paths, audio, neighbors)

## Why this matters

- Paths, norms, calibrations, and DBs are centralized so layout moves or deployments are low-touch. Avoid hardcoded strings; use helpers/env.
- Tests enforce import smoke and path literal heuristics to prevent drift.

- Roots:
  - `get_repo_root()`
  - `get_data_root()` (env `MA_DATA_ROOT`, default `./data`)
  - `get_calibration_root()` (env `MA_CALIBRATION_ROOT`, default `./calibration`)
  - `get_external_data_root()` (env `MA_EXTERNAL_DATA_ROOT`, default `<MA_DATA_ROOT>/external`)
  - `get_features_output_dir()` (future; use data root fallback)
- Pipeline defaults: `ma_config.pipeline` (env-overridable)
  - `HCI_BUILDER_PROFILE` (default `hci_v1_us_pop`)
  - `NEIGHBORS_PROFILE` (default `echo_neighbors_us_pop`)
  - `SIDECAR_TIMEOUT_SECONDS` (default `300`)
  - Sidecar preflight: `scripts/check_sidecar_deps.sh` must exist and be executable (guarded by tests).
  - Sidecar taxonomy (doc-only): extraction sidecars / aux extractors (tempo/key runner, lyric STT, TTC; read audio/primaries) vs. overlay sidecars (tempo_norms/key_norms; post-processing on existing features/lanes). Filenames remain unchanged.
  - Driver flags: `--skip-hci-builder` to skip HCI/rich/neighbor extras; `--skip-neighbors` sets `SKIP_CLIENT=1` for faster runs.
- DBs:
  - Lyric Intel DB: `get_lyric_intel_db_path()` (env `MA_DATA_ROOT` override)
  - Historical Echo DB: `get_historical_echo_db_path()` (env `MA_DATA_ROOT` override)
- Audio/HCI:
  - Calibration: `DEFAULT_HCI_CALIBRATION_PATH` / `AUDIO_HCI_CALIBRATION`
  - Market norms: `DEFAULT_MARKET_NORMS_PATH` / `AUDIO_MARKET_NORMS`
  - Audio policy: `DEFAULT_AUDIO_POLICY_PATH` / `AUDIO_HCI_POLICY`
  - HCI v2 calibration: `DEFAULT_AUDIO_V2_CALIBRATION_PATH` / `AUDIO_HCI_V2_CALIBRATION`
  - Datasets (targets/corpus/training): env `HCI_V2_TARGETS_CSV`, `HCI_V2_CORPUS_CSV`, `HCI_V2_TRAINING_CSV`
  - Loudness norms: `DEFAULT_LOUDNESS_NORMS_LOCAL_PATH`, `DEFAULT_MARKET_NORMS_LOUDNESS_PATH`, env `AUDIO_LOUDNESS_NORMS_OUT`
- Lyric LCI/TTC:
  - LCI: env `LYRIC_LCI_CALIBRATION`, `LYRIC_LCI_PROFILE`, `LYRIC_LCI_NORMS_PATH`
  - TTC: env `LYRIC_TTC_CONFIG`, `LYRIC_TTC_PROFILE`
- Lyric corpora:
  - Year-end lyrics CSV: `get_kaggle_year_end_lyrics_path()` (env `MA_KAGGLE_YEAR_END_LYRICS`, default `<MA_EXTERNAL_DATA_ROOT>/year_end/year_end_hot_100_lyrics_kaylin_1965_2015.csv`)
  - Hot100 lyrics+audio CSV: `get_hot100_lyrics_audio_path()` (env `MA_HOT100_LYRICS_AUDIO`, default `<MA_EXTERNAL_DATA_ROOT>/lyrics/hot_100_lyrics_audio_2000_2023.csv`)
  - Core1600 CSV: `get_core_1600_csv_path()` (env `MA_CORE1600_CSV`, default `<MA_DATA_ROOT>/core_1600_with_spotify_patched.csv`)
- Neighbors:
  - `resolve_neighbors_config` reads CLI > env (`LYRIC_NEIGHBORS_CONFIG`, `LYRIC_NEIGHBORS_LIMIT`, `LYRIC_NEIGHBORS_DISTANCE`) > JSON default `config/lyric_neighbors_default.json`.

Guidance

- Tools/CLIs should default via `ma_config` helpers and accept CLI overrides.
- When moving to a monorepo, update the helper defaults or set env vars; avoid embedding repo-relative strings in scripts.
- Tests include:
  - Import smoke (`tests/test_import_smoke.py`)
  - Path literal heuristic (`tests/test_path_literals.py`) to discourage new hard-coded `calibration/` or `data/` references outside ma_config.

ASCII map:

```bash
env (MA_DATA_ROOT, MA_CALIBRATION_ROOT, ...) --> ma_config.paths --> tools/CLIs
CLI flags (--profile, --calibration, --norms, --neighbors) ---------^
JSON configs (optional) -------------------------------------------^
```
