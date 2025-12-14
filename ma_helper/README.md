# ma_helper (packaged summary)

`ma_helper` is a modular monorepo helper with configurable adapters, roots, and no-write mode. This summary is packaged for installed users. Full guides live in `docs/` at the repo root.

## Quickstart (installed)

```bash
ma palette
ma list
ma test <project> --cache off|local|restore-only
ma affected --base origin/main
ma dashboard --json
```

## Config (`ma_helper.toml` or `.ma_helper.toml`)

```toml
adapter = "ma_orchestrator"
registry_path = "project_map.json"
state_dir = ".ma_helper_state"   # optional
log_file  = ".ma_helper_state/ma.log"  # optional
cache_dir = ".ma_cache"          # optional
[tasks]                          # optional aliases for `ma tasks`
test-all = "python tools/ma_orchestrator.py test-all"
```

Overrides:

- `--root <path>` or `MA_HELPER_ROOT` (root override)
- `MA_HELPER_ADAPTER` (adapter name)
- `MA_HELPER_REGISTRY` (registry path)
- `MA_HELPER_NO_WRITE=1` (read-only: disables cache/log/state writes)

Adapters:

- `ma_orchestrator` (default): wraps `tools/ma_orchestrator.py`.
- `mock`: reads `project_map.json` and stubs test/run (for demos or repos without an orchestrator).
- Future/custom adapters can be registered in `ma_helper.adapters.ADAPTERS` and selected via `adapter`/`MA_HELPER_ADAPTER`.

Common flows:

- `ma list`, `ma test <proj>`, `ma affected --base origin/main`, `ma run <proj>[:run|test]`, `ma dashboard --json|--live`, `ma verify`, `ma ci-plan --matrix`.
- Visual header: `ma --header list` (one-shot) or `ma --header-live test <project>` (sticky Rich header when available).

Read-only:

- Set `MA_HELPER_NO_WRITE=1` to disable cache/log/state writes (useful in CI or restricted environments).

Where to find full docs:

- Repo root: `docs/ma_helper_guide.md` (walkthroughs, debugging, examples).
- Repo root: `docs/ma_helper_config.md` (config keys, overrides, adapters, use cases).
