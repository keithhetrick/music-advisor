# Monorepo Plan (Canonical)

Combined snapshot of current repo state, prep work, and future blueprint. Supersedes `monorepo_plan.md`, `mono_prep_plan.md`, `monorepo_blueprint.md`, and `mono_repo_structure.md`.

## Current snapshot (what exists now)

- Audio engine relocated: code lives in `engines/audio_engine/src/ma_audio_engine`; legacy imports keep working via the canonical shim `src/ma_audiotools` and the `adapters/` alias. Tests cover bootstrap/sys.path guardrails. `aee_ml` and `plugins/` now live under `engines/audio_engine` with shims.
- Lyrics/STT relocated: code lives in `engines/lyrics_engine/src/ma_lyrics_engine` and `engines/lyrics_engine/src/ma_stt_engine`; root `ma_lyric_engine` is shimmed, `ma_stt_engine` extends `__path__`.
- TTC relocated: code lives in `engines/ttc_engine/src/ma_ttc_engine`; root `ma_ttc_engine` extends `__path__`.
- Host contracts relocated: code lives in `hosts/advisor_host_core/src/ma_host`; root `ma_host` extends `__path__`.
- Console scripts: canonical definitions now live in per-project pyprojects (audio/lyrics/ttc); the root table mirrors them for compatibility until callers flip. Old egg-info artifacts were removed.
- Remaining root concerns: legacy helpers and any unused tools; prune as usage clarifies (archives trimmed as callers migrate; `archive_shims/` currently empty).
- Data/config roots: `shared/calibration/` (symlink at root), `data/`, `features_output/`, plus helper configs under `infra/scripts/` and `tools/`.
- Config contract: source of truth in `shared/config` (re-exported via `ma_config`); path-literal guard (`tests/test_path_literals.py`) enforces helper usage. See `docs/config_paths.md`.
- Env-aware helpers already present: `ma_config.paths`/`audio`/`neighbors`/`constants`/`profiles`; widely used by lyric STT/WIP, TTC, neighbors, HCI audio v2 apply/fit/backfill, corpus/training builders, loudness fitter, echo injectors/importers, song_context builder.
- `hosts/advisor_host/` module has its own `pyproject.toml` and CLI (`ma-host`); uses `.client.*` payloads and advisory JSON.
- Root shims for console scripts exist (`ma-extract`, `ma-pipe`, `music-advisor-smoke`) alongside the package entrypoints; keep in sync until callers move to installed scripts.

## Current layout (mono-ready)

- `hosts/`
  - `advisor_host/` — Python host/chat shell (thin orchestrator; reusable concern packages inside).
- `engines/`
  - `audio_engine/` — core audio/HCI/TTC logic (relocated ma_audiotools + adapters + audio tools).
  - `lyrics_engine/` — lyric/STT flows (relocated ma_lyric_engine/ma_stt_engine and lyric tools).
  - `ttc_engine/` — TTC helpers (relocated ma_ttc_engine).
  - `recommendation_engine/` — core recommendation/advisory logic.
- `archive/`
  - `builder_pack/` — legacy GPT builder assets (prompts/router/policies); not used at runtime.
- `vendor/` — reserved for third-party/legacy deps.
- Other top-level dirs remain (data, scripts, notebooks, etc.); imports updated for the current layout.

## Prep plan (within this repo)

- Enforce package imports (minimize `sys.path` hacks); add import-smoke pytest (`--help` where feasible).
- Centralize remaining hard-coded paths via `ma_config` locator helpers; add lint to flag literal `calibration/` or `data/` outside `ma_config`.
- Add contract/constants module for bundle/DB keys; refactor producers/consumers (song_context_builder, lyric bundles, exports) to share constants; add contract/golden tests.
- Provide stable console entrypoints via pyproject for common flows (lyric-wip, lyric-wip-pipeline, rebake-lyrics, song-context, hci-simple, hci-audio-v2-apply/fit, ttc-sidecar, lyric-neighbors); keep backward-compatible shims.
- Document architecture, config/paths, and blueprint; keep tests green with lightweight smokes rather than heavy end-to-end runs.

## Future blueprint (docs-only)

Target layout (helper-friendly, matches engines/hosts/shared split):

- `engines/audio_engine` — Python audio/HCI/TTC with adapters/plugins/security.
- `engines/lyrics_engine` — lyric/STT flows and sidecars.
- `engines/recommendation_engine` — deterministic advisory layer.
- `hosts/advisor_host` (future: `hosts/macos_app`, `hosts/web_app`) — dumb orchestrators that call engines.
- `shared/config|security|calibration|utils|spine` — cross-engine helpers and data.
- `infra/` — CI/CD, Docker, orchestration scripts; `docs/` for architecture/monorepo.

Why current code survives moves:

- Paths resolved via `ma_config` (now under `shared/config`) with env overrides; moving calibration/data roots only changes helpers/env.
- Imports are package-based and shimmed; console entrypoints decouple CLI names from file locations.
- Contracts/keys centralized (ma_host.contracts planned), reducing string drift during moves.

## Migration checklist (when moving)

- Run pytest (includes import smoke, path-literal lint, contract checks).
- Run CLI import smoke (`tests/test_import_smoke.py`).
- Run WIP pipeline smokes (lyric STT/WIP, TTC, song_context) on sample data.
- Verify contracts vs golden fixtures (song_context/bundle).
- Adjust `ma_config` locator defaults if calibration/data roots move; set env overrides for staging.

Archived source docs: `docs/archive/monorepo/`.
