# Dev checks for host + recommendation engine

- Lint: `make lint` (ruff over `hosts/advisor_host` and `engines/recommendation_engine/recommendation_engine`).
- Typecheck: `make typecheck` (mypy using `hosts/advisor_host/pyproject.toml`).
- Tests: `make test` (pytest for host + recommendation engine suites).

Notes:
- `scripts/with_repo_env.sh` sets `PYTHONPATH` so editable source works without installs.
- CI installs `ruff` and `mypy`; locally install them (`pip install ruff mypy`) if not present.
- Optional extras (Redis session, Google token verification, rapidfuzz) can be installed via the host package extras when needed.
