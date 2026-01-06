# Dist Snapshot (Reproducible Bundle)

Use this when you need a clean, reproducible archive of the repo (source, docs, configs, wheels) without local caches or generated outputs.

## How to build

- Start from a clean git tree (no pending changes). Default refuses to run if dirty.
- From repo root: `./scripts/make_dist.sh`
- Output: `dist/music-advisor-YYYYMMDD.zip`
- Override name: `./scripts/make_dist.sh --name music-advisor-review`
- Allow dirty tree: `./scripts/make_dist.sh --dirty-ok` (still archives only HEAD tracked files; uncommitted changes are not included).

## What’s included

- All tracked files at HEAD: source (Python/Swift), configs, scripts, docs, automator workflows, vendored wheels (`wheels/`), lockfiles (`requirements.lock`, `pyproject.toml`), and assets such as `hosts/macos_app/AppIcon.appiconset/`.
- This lets you recreate the working audio_engine env via the cached Essentia wheel plus the frozen requirements. See `docs/deps/audio_engine_repro.md` and `docs/deps/engine_repro_all.md` for rebuild steps.

## What’s excluded

- Anything untracked or uncommitted (git archive only packages tracked files at HEAD).
- Generated outputs and caches that are gitignored (e.g., `.venv`, `.iconvenv`, `dist/`, `build/`, `logs/`, `data/features_output/`, `data/tmp/`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, editor folders, `.DS_Store`, swap files).
- If you need to include additional data artifacts, add/commit them before running the script.

## Rebuild reminder

- After unpacking: create Python 3.11.2 venv, install `wheels/essentia-*.whl`, then `pip install -r requirements.lock`.
- Per-engine sanity checks and flags live in `docs/deps/engine_repro_all.md`.
