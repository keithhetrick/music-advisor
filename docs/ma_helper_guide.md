# ma_helper Guide (Black-Box Ready)

This guide covers setup, configuration, common commands, adapter selection, troubleshooting, and examples for plugging `ma_helper` into a new repo.

## Quickstart (current repo)

```bash
python3 -m pip install -e .
ma palette
ma list
ma test <project> --cache off|local|restore-only
ma affected --base origin/main
ma dashboard --json
```

## Config file (`ma_helper.toml` or `.ma_helper.toml`)

Minimal:

```toml
adapter = "ma_orchestrator"         # orchestrator to use
registry_path = "project_map.json"  # registry location
[tasks]                              # optional task aliases for `ma tasks`
test-all = "python -m ma_helper test-all"
```

Paths (relative to root unless absolute):

```toml
state_dir = ".ma_helper_state"   # prefs/history/logs
log_file = ".ma_helper_state/ma.log"
cache_dir = ".ma_cache"
```

## Overrides

- CLI: `--root <path>` (force root)
- Env: `MA_HELPER_ROOT`, `MA_HELPER_ADAPTER`, `MA_HELPER_REGISTRY`
- Read-only: `MA_HELPER_NO_WRITE=1` (disables cache/log/state writes)

## Adapters (what and when)

- `ma_orchestrator` (default): wraps `tools/ma_orchestrator.py` (current monorepo). Use when that script exists.
- `mock`: reads `project_map.json` and stubs test/run (good for demos or repos without an orchestrator).
- Future/custom: register in `ma_helper.adapters.ADAPTERS` and set `adapter`/`MA_HELPER_ADAPTER` to point at your adapter. Use when a repo has a different orchestrator/inventory source.

## Common flows

- List projects: `ma list`
- Test one: `ma test <project> --cache local`
- Affected tests: `ma affected --base origin/main`
- Run target: `ma run <project>[:run|test]`
- Dashboard: `ma dashboard --json` or `ma dashboard --live` (rich)
- Quick gate: `ma verify`
- CI matrix dry-run: `ma ci-plan --base origin/main --matrix`
- Visual header: `ma --header list` (one-shot) or `ma --header-live test <project>` (sticky Rich header when available)

## Plugging into a new repo (example)

1. Copy `ma_helper` package into the new repo (or pip install if published).
2. Add `ma_helper.toml`:

```toml
adapter = "ma_orchestrator"
registry_path = "project_map.json"
[tasks]
test-all = "python -m ma_helper test-all"
```

3. Ensure your repo has `tools/ma_orchestrator.py` (or add your own adapter and set `adapter = "my_adapter"`).
4. Run: `ma --root . list` (from anywhere) to verify root discovery/adapter works.

## Logging & debugging

- Default log: `~/.ma_helper/logs/ma.log` (configurable via `log_file`).
- Read-only: set `MA_HELPER_NO_WRITE=1` (disables cache/log writes; first-run banners may reappear if prefs can’t be saved, but duplicates are suppressed per command).
- Debug a run: add `--dry-run` to print shell commands; use `MA_HELPER_NO_WRITE=1` if you want zero writes.
- If paths look wrong, pass `--root <path>` or set `MA_HELPER_ROOT`.

## Troubleshooting

- “Cannot load ma_orchestrator.py”: ensure `tools/ma_orchestrator.py` exists at the chosen root or switch `adapter`.
- “Cannot write prefs/cache”: expected when `MA_HELPER_NO_WRITE=1` or if your HOME is unwritable; specify `state_dir`/`cache_dir` or run read-only.
- Affected graph errors: install graphviz or use `--graph text/mermaid`.

## Tests (what’s covered)

- Config overrides and no-write: `tests/helper_unit/test_config.py`
- Adapter selection (ma_orchestrator): `tests/helper_unit/test_adapter_ma.py`
- CLI self-checks: `python3 tests/helper/self_check.py`
