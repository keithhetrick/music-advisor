# Audio Engine (ma_audio_engine)

Python audio/HCI/TTC pipeline extracted from the legacy `ma_audiotools` package. Code lives in `src/ma_audio_engine`; legacy imports (`ma_audiotools`, `adapters`) remain as shims for compatibility (canonical shim now at `src/ma_audiotools`).

## Structure

- `src/ma_audio_engine/` — analyzers, engines, adapters, policies, host helpers.
- `src/ma_audio_engine/adapters_src/` — canonical adapters; wrapped by `ma_audio_engine.adapters` and top-level `adapters/`.
- `plugins/` — plugin implementations (logging/sidecar/cache/exporter) now live here; root `plugins/` is a shim (archives removed).
- `src/ma_audio_engine/aee_ml/` — ML calibration helpers (shimmed from root `aee_ml`).
- `config/`, `security/` — shipped alongside for now; will be split into shared packages later.
- `pyproject.toml` — project metadata; uses editable workflow via `scripts/with_repo_env.sh`.

## Dev commands

- Activate repo env: `./scripts/with_repo_env.sh -m pytest -q` (runs full suite).
- Project-only tests (pseudo-helper): `python3 tools/ma_tasks.py test --project audio_engine` (runs root `tests/` today).
- CLI smoke: `./scripts/with_repo_env.sh -m pytest -q tests/test_cli_smoke.py`.
- Console scripts (pyproject) point at `ma_audio_engine.tools.*` wrappers; they forward to legacy `tools/` modules during migration.
- Quick test: `./scripts/quick_check.sh` (runs full suite); for a per-project fast check, run `python3 tools/ma_tasks.py test --project audio_engine`.

## Notes

- Keep new imports pointing at `ma_audio_engine.*`; shims (`ma_audiotools`, `adapters`) will be removed after downstreams flip. Archive shims have been pruned.
- Sys.path mutations are centralized in `adapters/bootstrap.py`; avoid adding new mutations elsewhere. Guarded by `tests/test_sys_path_mutation.py`.

## Developer experience

- Headless/CLI-first: iterate via CLI/tools/tests; no UI required.
- Quick smoke (with `PYTHONPATH=.`): `python -m ma_audio_engine.tools.pipeline_driver --help` or run a small extractor/sidecar via `tools/tempo_sidecar_runner.py`.
- Env/plugin selection drives wiring (cache/sidecar/export/logging plugins); see `docs/engine_dynamic_knobs.md` for knobs.
- Minimal smoke command: `PYTHONPATH=. python tools/tempo_sidecar_runner.py --audio tone.wav --out /tmp/tone.tempo.json`
