# Developer Workflow (Pseudo-Helper)

Lightweight orchestration for the Music Advisor monorepo lives in `tools/ma_orchestrator.py`. It keeps per-project commands readable and mimics Nx/Turborepo “affected” runs without extra tooling.

## Prereqs

- Python 3 available on PATH (uses `infra/scripts/with_repo_env.sh` to set PYTHONPATH/venv).
- Run commands from the repo root.

## One-shot bootstrap (recommended)

- Recommended (pinned): `make bootstrap-locked` (or `task bootstrap-locked`) uses `requirements.lock` for reproducible builds, installs all projects (editable), pulls data via `infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`, and runs `infra/scripts/quick_check.sh`. Requires network/manifest access.
- Fallback: `make bootstrap-all` (or `task bootstrap-all`) if you don’t want to use the lockfile.
- If downloads/build deps are blocked, see offline note below (`--no-build-isolation`).

## Common commands

- List projects: `python3 tools/ma_orchestrator.py list-projects` (also `make projects`).
- Single project tests: `python3 tools/ma_orchestrator.py test audio_engine` or `make test-audio-engine`.
- All tests: `python3 tools/ma_orchestrator.py test-all` or `make test`.
- Affected tests: `python3 tools/ma_orchestrator.py test-affected --base origin/main` or `make test-affected`.
  - Default base is `origin/main`; override with `--base <ref>` or `MA_AFFECTED_BASE=<ref>`.
- Run helpers (if configured):
  - Audio CLI help: `make run-audio-cli` (shows `ma_audio_engine.pipe_cli` usage).
  - Lyrics CLI help: `make run-lyrics-cli`.
  - TTC help: `make run-ttc-cli`.
  - Recommendation service help: `make run-reco-cli`.
  - Advisor host: `make run-advisor-host` (starts the FastAPI shim).
- Helper CLI (Nx/Turbo-style UX): `ma list` (or `python -m ma_helper` / `python tools/ma.py`), `ma tasks [--filter substr] [--json]`, `ma select` (interactive picker; fuzzy if prompt_toolkit is installed, stays open with back/blank), `ma affected --base origin/main [--parallel N]`, `ma test-all [--parallel N]`, `ma deps --graph mermaid|dot|svg|text`, `ma ci-plan --base origin/main` (print affected without running), `ma watch audio_engine [--cmd \"make test-audio\"]` (uses `entr` if present, else `watchfiles` fallback; install via `pip install watchfiles`), `ma welcome`, `ma doctor`, `ma sparse --set ...|--list|--reset`, `ma scaffold --type ... --name ...`, `ma smoke pipeline|full`, `ma lint`, `ma typecheck`, `ma format`, `ma favorites ...`, `ma rerun-last`. See `docs/tools/helper_cli.md` for the full command list and options.
- Taskfile alternative (if you use `task`): `task list-projects`, `task test-all`, `task test-affected base=origin/main`, `task test-audio`, `task run-audio-cli`, etc.
- Dependency view: `python3 tools/ma_orchestrator.py deps` (or `--reverse` for dependents).
- Per-project installs: `make install-audio`, `make install-lyrics`, `make install-ttc`, `make install-reco`, `make install-host`, `make install-host-core` (Taskfile equivalents exist).
- Offline/restricted installs: if pip cannot fetch build deps, add `--no-build-isolation`, e.g. `pip install --no-build-isolation -e engines/audio_engine ...` (or use `make install-projects` after activating your venv).
- External drives: cloning/running from an external disk works; create the venv on that disk and set `MA_DATA_ROOT` if you want data elsewhere.
- Local-only operation: after bootstrapping data once, all processing and outputs stay local (repo or `MA_DATA_ROOT`) with no external calls or uploads.
- Root/config overrides: use env vars (`MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`, etc.) to relocate data/calibration; `ma_config` path helpers respect these globally.
- Moving the repo: if you relocate the checkout, recreate the venv in the new location and keep your env overrides pointing at your data.
- Stale venv/shebang cleanup: if you previously installed from an old path (e.g., `MusicAdvisor`), run `make rebuild-venv` (or `task rebuild-venv`) to delete `.venv` with confirmation and recreate it.

## How “affected” works

- Uses `git diff --name-only <base>...HEAD` to find touched files.
- Maps changed paths to project roots from `project_map.json`.
- Expands to dependents (e.g., changing `shared/config` triggers audio/lyrics/ttc/host and root integration tests).
- Falls back to `test-all` if diff fails or no changes are detected.

## Fit for future helpers

- Project registry: `project_map.json` lists `path`, `tests`, `deps`, and optional `run` targets.
- Targets map 1:1 to future helpers:
  - Nx: `nx run audio_engine:test`, `nx affected:test --base=<ref>`.
  - Pants: `pants test engines/audio_engine::`, `pants --changed-since=<ref> test ::`.

## Standalone projects (modular mono-repo)

- Engines are individually installable/editable: `pip install -e engines/audio_engine` (also `lyrics_engine`, `ttc_engine`, `recommendation_engine`).
- Hosts are separate packages: `pip install -e hosts/advisor_host_core` (contracts) and `pip install -e hosts/advisor_host` (CLI/server chat host).
- Shared modules (`shared/config`, `shared/calibration`, `shared/core`, `shared/security`, `shared/utils`) stay as thin libs consumed by engines/hosts.
- Integration tests under `tests/` stitch everything together; project tests sit beside each project (`engines/*/tests`, `hosts/*/tests`).
- The orchestrator treats each project as a target, showcasing the mono-repo split while keeping cross-project affected detection.

| Type   | Project               | Path                          | Notes             |
| ------ | --------------------- | ----------------------------- | ----------------- |
| engine | audio_engine          | engines/audio_engine          | editable package  |
| engine | lyrics_engine         | engines/lyrics_engine         | editable package  |
| engine | ttc_engine            | engines/ttc_engine            | editable package  |
| engine | recommendation_engine | engines/recommendation_engine | editable package  |
| host   | advisor_host_core     | hosts/advisor_host_core       | contracts/helpers |
| host   | advisor_host          | hosts/advisor_host            | chat CLI/server   |
| shared | shared_config         | shared/config                 | shared lib        |
| shared | shared_calibration    | shared/calibration            | shared lib        |
| shared | shared_core           | shared/core                   | shared lib        |
| shared | shared_security       | shared/security               | shared lib        |
| shared | shared_utils          | shared/utils                  | shared lib        |
| integ  | root_integration      | tests                         | full-stack tests  |
