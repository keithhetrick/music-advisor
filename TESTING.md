# Testing Guide

## Primary commands

- Full suite: `make quick-check`
- Affected-only: `infra/scripts/test_affected.sh` (uses git diff; falls back to quick-check)
- Project-specific: `make test-project PROJECT=audio_engine` (or lyrics_engine, ttc_engine, recommendation_engine, advisor_host)

Project shortcuts:

- `make test-audio-engine`
- `make test-lyrics-engine`
- `make test-ttc-engine`
- `make test-recommendation-engine`
- `make test-advisor-host`

## When to run what

- Small/targeted change: `infra/scripts/test_affected.sh`
- Feature branch before PR: `make quick-check`
- Before tagging/release: `make clean && make quick-check`

## Fixtures and data

- Tests rely on in-repo fixtures; no external data required.
- Outputs write to temp dirs during tests; `make clean` clears caches if needed.

## Lint/typecheck (host)

- `make lint` / `make typecheck` run the host-focused linters/type checks.

## Troubleshooting tests

- If path-related failures occur, ensure `MA_DATA_ROOT` is unset or points to a writable location.
- If dependencies are missing, reinstall with `pip install -r requirements.txt && pip install -r requirements.lock || true`.
