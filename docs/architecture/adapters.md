# Adapters Overview

Centralized reference for adapter modules, their config/env knobs, side effects, and example usage. Each adapter also carries inline docstrings with the same details.

## Audio / Tempo / Sidecar

- `adapters/audio_loader_adapter.py`
  - Config: `config/audio_loader.json` (backend, mono); env `MAX_AUDIO_DURATION_SEC` (ffmpeg cap).
  - Side effects: ffprobe/ffmpeg subprocesses; temp WAV during fallback.
  - Usage: `load_audio_mono(path, sr=44100)` (librosa → ffmpeg fallback).
- `adapters/confidence_adapter.py`
  - Config: `config/tempo_confidence_bounds.json` (per-backend bounds/labels).
  - Usage: `normalize_tempo_confidence(raw, backend="essentia")`; `confidence_label(score, backend, raw=raw_conf)`.
- `adapters/backend_registry_adapter.py`
  - Config: `config/backend_registry.json` (enabled backends, default/per-backend sidecar cmd).
  - Usage: `list_supported_backends()`, `get_sidecar_cmd_for_backend("essentia")`, `is_backend_enabled("madmom")`.
- `adapters/beatlink_adapter.py`
  - CLI shim emitting minimal external tempo/key payload; merges sibling `.beat.json` if present.

## Logging / Settings / Preflight

- `adapters/logging_adapter.py`
  - Config: env `LOG_JSON`, `LOG_REDACT`, `LOG_REDACT_VALUES`, `LOG_SANDBOX`; file `config/logging.json` (prefix, redact, sandbox).
  - Usage: `make_logger(...)`, `make_structured_logger(...)`, `sandbox_scrub_payload(payload)`.
- `adapters/settings_adapter.py`
  - Config: `config/settings.json` (cache*dir, tempo_conf bounds, qa_policy, logging defaults); env LOG*\*; CLI overrides.
  - Usage: `load_log_settings(args)`, `load_runtime_settings(args)`.
- `adapters/preflight_adapter.py`
  - Usage: `validate_root_dir`, `validate_root_list`, `ensure_parent_dir`, `require_paths` to guard inputs before heavy work.
- `adapters/cli_adapter.py`
  - Usage: add common argparse flags (`log-json`, `log-sandbox`, `preflight`, `qa-policy`) and apply env fallbacks.
- `adapters/bootstrap.py`
  - Usage: `ensure_repo_root()` to add repo/src to `sys.path` in entrypoints.
- `adapters/time_adapter.py`
  - Usage: `utc_now_iso()` for UTC timestamps.

## Cache / Hash / QA / Neighbors

- `adapters/cache_adapter.py`
  - Config: `config/cache.json` (default cache_dir/backend).
  - Usage: `get_cache(cache_dir, backend="disk|noop")`; side effects when backend=disk.
- `adapters/hash_adapter.py`
  - Config: `config/hash.json` (algorithm, chunk_size).
  - Usage: `get_hash_params()`, `hash_file(path, algorithm, chunk_size)`.
- `adapters/qa_policy_adapter.py`
  - Config: `config/qa_policy.json` (override thresholds).
  - Usage: `load_qa_policy("strict", overrides=...)`.
- `adapters/neighbor_adapter.py`
  - Usage: `write_neighbors_file(path, payload, max_neighbors=..., max_bytes=..., warnings=list, debug=logger)`; enforces schema/size guards; mutates warnings list.

## Service/Plugin bridge

- `adapters/service_registry.py`
  - Plugins: env `MA_EXPORTER_PLUGIN`, `MA_LOGGING_PLUGIN`.
  - Usage: `get_exporter()`, `get_logger()/get_structured_logger()`, `get_qa_policy()`, `get_cache()`, `scrub_payload_for_sandbox()`.
- `adapters/plugin_loader.py`
  - Usage: `load_factory(group, name, factory_attr="factory")` to load plugin factories under `plugins/<group>/<name>.py`.

## Config helpers

- `adapters/config_adapter.py`
  - Usage: `resolve_config_value(cli, env_var, default, coerce)`, `overlay_config(base, overrides)`, `build_config_components(...)` for fingerprints.
- `ma_config/paths.py`
  - Env overrides: `MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`, `MA_EXTERNAL_DATA_ROOT`, `MA_KAGGLE_YEAR_END_LYRICS`, `MA_HOT100_LYRICS_AUDIO`, `MA_CORE1600_CSV`, `MA_SPINE_ROOT`, `MA_SPINE_BACKFILL_ROOT`, `MA_SPINE_MASTER`, `MA_KAGGLE_YEAR_END_LYRICS`.
  - Usage: path helpers for data/calibration/features/DBs.
- `ma_config/profiles.py`
  - Usage: `resolve_profile_config(...)` with precedence CLI > env > JSON > default.
- `ma_config/audio.py`
  - Env overrides: `AUDIO_HCI_PROFILE`, `AUDIO_HCI_CALIBRATION`, `AUDIO_MARKET_NORMS`, `AUDIO_HCI_POLICY`, `AUDIO_HCI_V2_CALIBRATION`, `HCI_V2_TARGETS_CSV`, `HCI_V2_CORPUS_CSV`, `HCI_V2_TRAINING_CSV`, `AUDIO_LOUDNESS_NORMS_OUT`.
  - Usage: resolve calibration/policy/norms paths + load JSON safely.
- `ma_config/pipeline.py`
  - Defaults: `HCI_BUILDER_PROFILE_DEFAULT`, `NEIGHBORS_PROFILE_DEFAULT`, `SIDECAR_TIMEOUT_DEFAULT`; overridden via env or pipeline driver `--config`.

## Validation hooks

- Use `tools/validate_io.py` with schemas under `schemas/` for feature/merged/client/HCI artifacts.
- Sidecar deps preflight: `scripts/check_sidecar_deps.sh` must remain present/executable (tests enforce).
