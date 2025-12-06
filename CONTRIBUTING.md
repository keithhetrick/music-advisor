# Contributing to Music Advisor

Thanks for helping improve the monorepo. This is the canonical workflow; keep everything reproducible and local-first.

## Setup

- Clone: `git clone git@github.com:<org>/music-advisor.git && cd music-advisor`
- Python: `python3 -m venv .venv && source .venv/bin/activate`
- Install: `pip install -r requirements.txt && pip install -r requirements.lock || true`
- Bootstrap data (optional): `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json` (writes to `data/public`; MA_DATA_ROOT overridable).

## Fast checks

- Quick smoke: `make quick-check` (full suite).
- Affected-only: `infra/scripts/test_affected.sh` (uses git diff, falls back to quick-check).
- Clean caches: `make clean` (safe) or `make deep-clean` (git clean -xfd, prompts by default).

## Coding conventions

- Keep imports relative to project namespaces (`engines/*`, `hosts/*`, `shared/*`); avoid sys.path hacks.
- Add/update tests alongside code changes. Use existing fixtures in `tests/fixtures` when possible.
- Run linters if you touch host code: `make lint` / `make typecheck` for advisor_host (ruff + mypy).
- Style: default to black/pep8 conventions (follow existing formatting); avoid trailing whitespace and large reformat-only PRs.
- Prefer path helpers (MA_DATA_ROOT via `shared.config.paths`/`shared.paths`) over hardcoded paths.

## Pull request checklist

- [ ] Tests: `make quick-check` (or `infra/scripts/test_affected.sh` for scoped changes).
- [ ] Docs: update any referenced paths/commands; keep README/doc links valid.
- [ ] Data: do not commit raw audio/dbs; ensure manifests point only to allowed public assets.
- [ ] Security: no secrets, tokens, or presigned URLs in code, manifests, or logs.
- [ ] Commits/PR titles: keep them descriptive (e.g., “audio_engine: fix tempo overlay edge case”).

## Reporting issues

- For bugs, include: command run, expected vs actual, env (OS/Python), and relevant logs from `logs/` if available (redact paths if needed).

## Release hygiene (summary)

- `make clean` → `make quick-check` → update CHANGELOG.md → tag/version per RELEASE.md.
