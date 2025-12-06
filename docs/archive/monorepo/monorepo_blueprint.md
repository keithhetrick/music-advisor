# Monorepo Blueprint (future, docs-only)

Proposed layout (no moves yet)

- /apps/musicadvisor_cli: user-facing CLI wrappers/entrypoints.
- /apps/musicadvisor_host: host/web/GUI orchestration.
- /packages/ma_config: config locator, profiles, constants, contracts.
- /packages/ma_lyric_engine, /packages/ma_ttc_engine, /packages/ma_audio_engine, /packages/ma_host: domain engines/utilities.
- /shared/calibration: shared calibration/norms/policies.
- /shared/data: datasets (or keep external if large).
- /infra: CI/CD, Docker, tooling.

Why current code survives moves

- Paths are resolved via `ma_config` helpers with env overrides; changing calibration/data roots requires updating helpers/env, not tools.
- Imports are package-based; console entrypoints (pyproject) decouple CLI names from file locations.
- Contracts/keys centralized (ma_host.contracts), reducing string drift during moves.

Migration checklist (when moving)

- Run `pytest` (includes import smoke, path-literal lint, contract checks).
- Run CLI import smoke (`tests/test_import_smoke.py`).
- Run WIP pipeline smokes (lyric STT/WIP, TTC, song_context) on sample data.
- Verify contracts vs golden fixtures where available (song_context/bundle).
- Adjust `ma_config` locator defaults if calibration/data roots move; set env overrides for staging.
