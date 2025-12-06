# TTC Engine (ma_ttc_engine)

Tempo/TTC helpers relocated from the legacy `ma_ttc_engine` package. Code lives in `src/ma_ttc_engine`; root `ma_ttc_engine` package extends `__path__` to the new location for compatibility.

## Structure

- `src/ma_ttc_engine/` — chorus detection and TTC feature helpers.
- `pyproject.toml` — project metadata; uses editable workflow via `scripts/with_repo_env.sh`.

## Dev commands

- Full suite: `./scripts/with_repo_env.sh -m pytest -q` (shared tests).
- Project-only (pseudo-helper): `python3 tools/ma_tasks.py test --project ttc_engine` (runs root `tests/` today).
- Quick import smoke: `PYTHONPATH=engines/ttc_engine/src python -c \"import ma_ttc_engine; print(ma_ttc_engine.__file__)\"`.

## Notes

- Prefer imports from `ma_ttc_engine.*`; shim remains until downstreams flip and `engines/ttc_engine/src` is on `PYTHONPATH`.

## Developer experience

- Headless/CLI-first: run tools/tests; no UI required.
- Quick smoke (with `PYTHONPATH=.`): `python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json` or `pytest` under `engines/ttc_engine/tests`.
- Dynamic knobs: TTC sidecar env fallback via `TTC_OPTS` (seconds-per-section/profile), logging via `LOG_JSON`/redaction; see `docs/pipeline_dynamic_knobs.md` and `docs/engine_dynamic_knobs.md`.
- Minimal smoke: `PYTHONPATH=. python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json`
