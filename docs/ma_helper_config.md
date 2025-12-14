# ma_helper Configuration

`ma_helper` can run as a drop-in helper with a minimal config file plus env/CLI overrides. Defaults are safe; you can choose to run fully read-only.

## Config file

Create `ma_helper.toml` (or `.ma_helper.toml`) at repo root:

```toml
# Which orchestrator adapter to use (default: "ma_orchestrator")
adapter = "ma_orchestrator"

# Project registry path (default: project_map.json)
registry_path = "project_map.json"

# Optional: state/log/cache locations (relative to root unless absolute)
state_dir = ".ma_helper_state"
log_file = ".ma_helper_state/ma.log"
cache_dir = ".ma_cache"

[tasks]
# Optional task aliases for `ma tasks`
test-all = "python tools/ma_orchestrator.py test-all"
```

## Overrides

- `--root <path>`: force repo root (bypass discovery).
- `MA_HELPER_ROOT`: root override (env).
- `MA_HELPER_ADAPTER`: adapter name override.
- `MA_HELPER_REGISTRY`: registry path override.
- `MA_HELPER_NO_WRITE=1`: run read-only (disables cache/log/state writes).

## State/log/cache

- Defaults: state under `~/.ma_helper`, cache under `<root>/.ma_cache`.
- Respect `state_dir`, `cache_dir`, `log_file` from config; `MA_HELPER_NO_WRITE` disables persistence.

## Task aliases

- `[tasks]` entries populate `ma tasks`. If omitted, built-in aliases are empty by default.

## Adapters

- **ma_orchestrator**: wraps `tools/ma_orchestrator.py` (current monorepo orchestrator). Use this in the Music Advisor repo or any repo that provides the same orchestrator script/API.
- (Future adapters): you can register additional adapters in `ma_helper.adapters.ADAPTERS` and select them via `adapter` or `MA_HELPER_ADAPTER`. This is intended for other monorepos with different orchestrators or inventory sources.

Use cases:

- Keep defaults for current repo: no config needed; uses ma_orchestrator, project_map.json, default cache/state.
- Custom registry path or task palette: set `registry_path` or `[tasks]`.
- Run in read-only mode (CI smoke): set `MA_HELPER_NO_WRITE=1`.
- Point at a different checkout or sparse tree: use `--root` or `MA_HELPER_ROOT`.
- Swap orchestrator for another monorepo: add/register an adapter and set `adapter`/`MA_HELPER_ADAPTER`.
