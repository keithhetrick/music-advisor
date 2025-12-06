# Monorepo Overview (Current → Target)

Status: ✅ Last verified after 12-file payload rollout (Automator/quick-check aligned; includes tempo_norms sidecar + tempo overlay injection).

Authoritative snapshot of what lives where today, plus the intended target layout and compatibility shims. Keep this file in sync with moves; treat it as the single source for “where is X?” during the transition.

## Current state (projects and entrypoints)

- Audio engine moved: code lives in `engines/audio_engine/src/ma_audio_engine`; legacy imports still work via `src/ma_audiotools` (canonical shim) and the `adapters/` alias. Adapters/bootstrap sys.path hacks are centralized and covered by tests. Audio ML helpers (`aee_ml`) and plugins now live under `engines/audio_engine/` with legacy shims.
- Lyrics/STT moved: code lives in `engines/lyrics_engine/src/ma_lyrics_engine` and `engines/lyrics_engine/src/ma_stt_engine`; root `ma_lyric_engine` package is shimmed, and `ma_stt_engine` extends `__path__` to the new package.
- TTC moved: code lives in `engines/ttc_engine/src/ma_ttc_engine`; root `ma_ttc_engine` extends `__path__`.
- Host contracts moved: code lives in `hosts/advisor_host_core/src/ma_host`; root `ma_host` extends `__path__`.
- Root package `musicadvisor-audiotools`: console scripts table exists for compatibility but points at the new package namespaces. Canonical definitions live in per-project `pyproject.toml` (audio/lyrics/ttc); prefer installing/running via those packages (e.g., `make install-projects`). Plan to drop root scripts after downstreams flip; legacy egg-info artifacts were removed.
- Root shims have been removed and compatibility packages archived (`archive/legacy_src/`); console scripts in `.venv/bin` now point at `ma_audio_engine.*`. Module entry points also work (`python -m ma_audio_engine.pipe_cli`).
- Shared namespace prep: `shared/config/__init__.py` re-exports `ma_config` (plus per-module shims), `shared/security/__init__.py` re-exports `security`; `shared/README.md` documents the plan.
- Project metadata lives in `project_map.json` and powers `tools/ma_orchestrator.py` (Make targets: `make test`, `make test-affected`, `make projects`, `make run-*`). `tools/ma_tasks.py` remains as a shim for older entrypoints.
- Projects already split:
  - `engines/audio_engine` (pyproject + tests via root `tests/` today).
  - `engines/recommendation_engine` (pyproject + tests).
  - `hosts/advisor_host` (pyproject + tests).
- Not yet moved: `tools/` CLIs (shimmed via package wrappers) and some legacy helpers; remaining consolidation is tracked in pseudo-helper metadata. Root shims (`ma-extract`, `ma-pipe`, `music-advisor-smoke`, `always_present.py`, `extract_cli.py`) have been removed; downstream callers should rely on installed console scripts or module paths.
- Data/config roots in use: `shared/calibration/`, `config/`, `data/`, `datahub/`, `schemas/`, `policies/`, `presets/`, `features_external/`; generated artifacts under `data/features_output/`, `client_audio_features/`, `logs/`. The `data/` directory stays in the tree but its contents are git-ignored by default to avoid committing raw audio/databases.
  - Data subfolders: `data/public` (shareable/bootstrap assets), `data/private` (local-only), `data/historical_echo`, `data/features_output`.
- Full-app smoke: `make e2e-app-smoke` (tone → `python -m ma_audio_engine.pipe_cli` → advisor_host CLI on sample payload).
- Synthetic pipeline fixtures (reference success shapes): `tests/fixtures/pipeline_sample/` with validation in `tests/test_pipeline_fixture_shapes.py`.
- Full-app smoke outputs: uses a temp dir (e.g., `/tmp/ma_e2e_xxxx`), writes `tone.wav`, `advisory.json`, `host_out.json`, then cleans up. No artifacts remain in the repo.
- Infra alignment: orchestration moved under `infra/scripts/` and `infra/docker/`; use these paths directly.
- Shared utils namespace introduced at `shared/utils/` (currently re-exporting `shared.core`) to match the target layout.
- CI stub: `infra/scripts/ci_local.sh` runs the full quick check as a local/pre-CI runner.
- CI workflow: `.github/workflows/ci.yml` runs the quick check on push/PR.
- Data bootstrap: `infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json` to download required assets into `data/` (populate manifest URLs/checksums).
- Data/bootstrap details: see `docs/data_bootstrap.md` for layout, S3/HTTPS bootstrap, and env overrides.

## Current high-level layout (implemented)

```ascii
engines/
  audio_engine/          # ma_audio_engine (extractors, pack_writer, echo probe, adapters)
  lyrics_engine/         # lyric/STT packages
  ttc_engine/            # TTC estimator tools
  recommendation_engine/ # existing package/tests
hosts/
  advisor_host/          # host CLI/API
  advisor_host_core/     # host contracts/helpers
shared/
  config/                # config resolution, profiles, paths
  calibration/           # calibration/norms/policies/assets (tracked)
  utils/                 # shared helpers
infra/
  scripts/               # orchestration (data_bootstrap, data_manifest, data_sync_public, quick_check)
  docker/                # container stubs
docs/                    # architecture, ops, pipeline, research (current/archived)
data/                    # git-ignored runtime data root
  public/                # S3-backed, safe to share (manifest allowlist)
  private/               # local-only
  features_output/       # generated payloads (Automator, pipeline)
tools/                   # legacy shims (being migrated into engines/shared)
logs/                    # Automator run logs

## Standalone projects (modular split)

- Engines: `engines/audio_engine`, `engines/lyrics_engine`, `engines/ttc_engine`, `engines/recommendation_engine` — each has its own `pyproject.toml` and tests and can be installed editable (`pip install -e ...`).
- Hosts: `hosts/advisor_host_core` (contracts/helpers) and `hosts/advisor_host` (CLI/server chat host) are separate packages with their own tests.
- Shared libs: `shared/config`, `shared/calibration`, `shared/core`, `shared/security`, `shared/utils` provide cross-cutting helpers; no tests of their own yet, but they flow into affected detection.
- Integration: root `tests/` exercises the full pipeline/host stack and depends on the above projects.

## Pseudo-helper + future mapping

- Entry point: `python3 tools/ma_orchestrator.py ...` or Make targets (`make test`, `make test-affected`, `make test-audio-engine`, `make run-audio-cli`).
- Registry: `project_map.json` defines `path`, `tests`, `deps`, and optional `run` targets; shared modules (config/calibration/core/security/utils) are included for affected expansion.
- Affected logic: `git diff --name-only <base>...HEAD` → match project paths → add dependents → run pytest via `infra/scripts/with_repo_env.sh`.
- Future helper parity:
  - Nx: `audio_engine` → `nx run audio_engine:test`, `advisor_host` → `nx run advisor_host:test`, affected → `nx affected:test --base=<ref>`.
  - Pants: `audio_engine` → `pants test engines/audio_engine::`, `advisor_host` → `pants test hosts/advisor_host::`, affected → `pants --changed-since=<ref> test ::`.
- Offline installs: if build deps can’t be fetched, use `--no-build-isolation` with editable installs (e.g., `pip install --no-build-isolation -e engines/audio_engine`), or `make install-projects` after activating `.venv`.
- One-shot bootstrap: `make bootstrap-all` (or `task bootstrap-all`) creates `.venv`, installs all projects (editable), runs data bootstrap (`infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`), and executes `infra/scripts/quick_check.sh` for a fresh smoke (requires network/manifest access).
- External storage: the repo can live/run on an external disk; create the venv there and use `MA_DATA_ROOT` if you want data elsewhere.
- Local-only: once bootstrapped, all processing and outputs stay within the repo (or `MA_DATA_ROOT`) with no external calls or uploads.
- Env overrides: `ma_config` path helpers honor `MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`, and related envs globally; set them once to redirect data/calibration roots.
- Moving the repo: if you relocate the checkout, recreate the venv in the new path and retain your env overrides to keep using the same data roots.

## Adding a new project (modularity checklist)

- Layout: create under `engines/` or `hosts/` (or `shared/` for libs) with its own `pyproject.toml`, `src/`, and `tests/`.
- Registry: add an entry to `project_map.json` with `path`, `tests`, `type`, `deps` (other project names), and optional `run` command.
- Orchestrator: no code changes needed; `tools/ma_orchestrator.py` will pick up the new entry for `list-projects`, `test`, `test-affected`, and `run`.
- Tasks: if you want Make/Task targets, add a thin wrapper pointing to the orchestrator (`make test-<name>`, `task test-<name>`).
- Installability: optional but recommended—add `pip install -e <project>` targets to Makefile/Taskfile for easy standalone usage.
```

Reality vs plan

- Root is cleaned: docker/scripts live under infra/, data is partitioned, outputs live under data/features_output/.
- Pipeline emits the 12-file payload: features, sidecar, tempo_norms, merged, hci, ttc, neighbors, client/client.rich txt/json, run_summary.
- Automator/Quick Action runs `automator.sh` to produce the payload + echo injection; quick-check scripts live under infra/scripts/.
- Data bootstrap uses `infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`; only data/public is fetched, calibration ships in `shared/calibration/`.
- See also: ops/commands (`docs/ops/commands.md`) for quick commands and pipeline docs (`docs/pipeline/README_ma_audio_features.md`, `docs/pipeline/PIPELINE_DRIVER.md`) for payload details.

Each project keeps its own `pyproject.toml`, `src/` package, `tests/`, and README, so it can be extracted later with minimal surgery.

## Compatibility/shim policy

- Keep the root executables (`ma-extract`, `ma-pipe`, `music-advisor-smoke`) as thin wrappers that call the new project packages; retire them once all callers use installed console scripts.
- Maintain import-smoke coverage (`tests/test_import_smoke.py`) for shims and new package paths; add shims when moving modules, then remove after downstreams flip (archives pruned as they become unused; `archive_shims/` currently empty).
- Config/paths source of truth lives in `shared/config` (re-exported via `ma_config`); see `docs/config_paths.md`. Path-literal guard (`tests/test_path_literals.py`) enforces use of helpers over hard-coded `calibration/`/`data/` strings.
- Prefer `ma_config` (to be relocated under `shared/config`) for all path lookups; avoid hard-coded `calibration/` or `data/` literals in code or docs.

## Doc update expectation

- When files move, update: `docs/architecture/README.md`, `docs/architecture/repo_structure.md`, `docs/monorepo/plan.md`, this file, and any doc that references concrete paths (pipeline, host/chat, calibration).
- Archived docs in `docs/archive/` can remain with a pointer to this overview.
