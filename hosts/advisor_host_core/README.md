# Advisor Host Core (ma_host)

Host contracts/helpers relocated from the legacy `ma_host` package. Code lives in `src/ma_host`; root `ma_host` package extends `__path__` to the new location for compatibility.

## Structure

- `src/ma_host/` — contracts, song_context helpers, neighbor utilities.
- `pyproject.toml` — project metadata; uses editable workflow via `scripts/with_repo_env.sh`.

## Dev commands

- Full suite: `./scripts/with_repo_env.sh -m pytest -q` (shared tests).
- Project-only (pseudo-helper): `python3 tools/ma_tasks.py test --project advisor_host_core` (runs root `tests/` today).
- Quick import smoke: `PYTHONPATH=hosts/advisor_host_core/src python -c "import ma_host; print(ma_host.__file__)"`.

## Notes

- Prefer imports from `ma_host.*` with `hosts/advisor_host_core/src` on `PYTHONPATH`; shim stays until downstreams are updated.
