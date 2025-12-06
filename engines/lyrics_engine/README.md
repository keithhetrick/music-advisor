# Lyrics Engine (ma_lyrics_engine / ma_stt_engine)

Lyrics/STT pipeline relocated from the legacy `ma_lyric_engine` and `ma_stt_engine` packages. Code lives in `src/ma_lyrics_engine` and `src/ma_stt_engine`; legacy imports remain via shims at repo root (archive shims removed).

## Structure

- `src/ma_lyrics_engine/` — lyric ingestion, lanes/LCI, bundles, exports.
- `src/ma_stt_engine/` — STT helpers (whisper backend).
- `tools/` — lyric CLIs (WIP pipeline, neighbors, STT sidecar, reports, intel ingest).
- `config/` — lyric neighbors defaults (copied from root `config/` for now).

## Developer experience

- Headless/CLI-first: run tools and tests; no UI required.
- Quick smoke (with `PYTHONPATH=.`): `python engines/lyrics_engine/tools/lyric_wip_pipeline.py --help` or run a whisper STT helper.
- Dynamic knobs (models/commands/paths) via env; see `docs/engine_dynamic_knobs.md`.
- Minimal smoke: `PYTHONPATH=. python engines/lyrics_engine/tools/lyric_wip_pipeline.py --help` (or run STT helper with a short audio clip).

## Dev commands

- Activate repo env: `./scripts/with_repo_env.sh -m pytest -q` (full suite).
- Project-only tests (pseudo-helper): `python3 tools/ma_tasks.py test --project lyrics_engine` (runs root `tests/` today).
- CLI smoke: `./scripts/with_repo_env.sh python tools/lyric_wip_pipeline.py --help` (or neighbors/STT sidecar).
- Quick help targets: `make lyrics-cli-help` runs `lyric_wip_pipeline.py --help` with the right PYTHONPATH.
- Quick test: `./scripts/quick_check.sh` (full suite); a narrow import smoke is `python3 -m ma_lyrics_engine.__init__` with `PYTHONPATH=engines/lyrics_engine/src`.

## Notes

- Shims: root `ma_lyric_engine` modules forward to `ma_lyrics_engine.*`; `ma_stt_engine/__init__.py` extends `__path__` to the new package. Archive shims were pruned; remove root shims after downstreams flip to `ma_lyrics_engine`/`ma_stt_engine` imports with `engines/lyrics_engine/src` on `PYTHONPATH`.
- Keep sys.path mutations centralized (use `adapters.bootstrap.ensure_repo_root` in scripts as needed).
