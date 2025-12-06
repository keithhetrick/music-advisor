# Config and Paths Contract

Source of truth for repo paths and config defaults lives in `shared/config/` (re-exported via `ma_config` for compatibility). Callers should avoid hard-coded `calibration/` or `data/` literals and instead use these helpers:

- Path helpers: `ma_config.paths.get_repo_root`, `get_data_root`, `get_calibration_root`, `get_external_data_root`, `get_features_output_root`, `get_historical_echo_db_path`, `get_lyric_intel_db_path`, `get_spine_root`, etc. All support env overrides (e.g., `MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`).
- Pipeline defaults: `ma_config.pipeline` for driver profiles/timeouts; honor CLI/env/JSON precedence rather than embedding constants.
- Profiles/constants: `ma_config.profiles`, `ma_config.constants`, `ma_config.neighbors`, `ma_config.audio` for shared enums, neighbors config, and policy paths.

Guardrails:

- `tests/test_path_literals.py` flags new hard-coded `calibration/` or `data/` literals outside `ma_config/shared` (with a small allowlist). Add new paths by extending `ma_config` rather than bypassing it.
- `scripts/quick_check.sh` runs the guard by default as part of pytest.

When adding a new path or config knob:

1. Add it to `shared/config/` (and `ma_config` will pick it up automatically).
2. Update this doc with the env override (if any).
3. Keep literals out of code; prefer helpers so env overrides work across hosts/engines and future monorepo moves.
