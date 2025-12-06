# shared/

Placeholder namespace for common packages (config, calibration assets, utils) as we split engines/hosts. Source of truth for config lives here; `ma_config` is a thin compatibility wrapper that re-exports `shared.config.*`.

Currently re-exports:

- `ma_config` via `shared/config/__init__.py`
- `core` via `shared/core/__init__.py` (placeholder shims; `ma_core` points here)
- `security` via `shared/security/__init__.py`
- `utils` via `shared/utils/__init__.py` (re-exporting shared.core and path helpers as a utilities home)
- `calibration/` now lives under `shared/calibration/`.

Use `shared.config` (or `ma_config` while callers migrate) instead of hard-coded paths. See `docs/config_paths.md` for the contract and the path-literal guard test.

Quick checks:
- Full suite: `./scripts/quick_check.sh`
- Import smoke: `PYTHONPATH=shared python -c "import config.paths, security.subprocess; print('ok')"`

Legacy compatibility packages have been archived under `archive/legacy_src/`; active shared code lives here. Console scripts now point at the canonical engine/host modules (`ma_audio_engine.*`).
