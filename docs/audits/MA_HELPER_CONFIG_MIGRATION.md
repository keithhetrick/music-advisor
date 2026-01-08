# ma_helper Config Migration Plan

## ✅ Completion Status

**Status**: ✅ **COMPLETE** (Tasks 31-38, completed 2026-01-07)

**Summary**:

- All 14 mutable globals eliminated
- `apply_config()` function removed
- RuntimeConfig frozen dataclass created
- 24 consumer files migrated
- All tests passing

**Commits**:

- Task 31: `68cf1b8` - Created RuntimeConfig frozen dataclass
- Task 32: `5ebfd06` - Migrated visual.py to RuntimeConfig
- Task 33: `3a23fa7` - Migrated helpdesk.py to RuntimeConfig
- Task 34: `e40dd08` - Migrated testflow.py to RuntimeConfig
- Task 35: `5d0e1bb` - Migrated favorites.py to RuntimeConfig
- Task 36: `4a0ffb6` - Migrated runtime.py, smoke.py, scaffold.py, chatdev.py to RuntimeConfig
- Task 37: `34dbde2` - Migrated adapters, core, and tui to RuntimeConfig
- Task 38: `04e8fcb` - Removed apply_config() and all global mutations

**Verification**:

- ✅ `grep -rn "global " ma_helper/ --include="*.py"` returns 0 results
- ✅ `grep -rn "apply_config" ma_helper/ --include="*.py"` returns 0 results
- ✅ `pytest tests/helper_unit/test_config.py -v` passes (3/3 tests)
- ✅ All ma_helper commands work: `list`, `doctor`, `dashboard`, etc.

---

## Executive Summary

This document ~~analyzes~~ analyzed the ~~current~~ previous global configuration pattern in ma_helper and ~~proposes~~ documented a migration to immutable configuration objects. The ~~current~~ previous system had **14 mutable globals** across 2 files that were mutated at runtime via `apply_config()` and the `--root` flag.

**Files in scope:**

- [ma_helper/core/env.py](../../ma_helper/core/env.py) (11 mutable globals)
- [ma_helper/cli_app.py](../../ma_helper/cli_app.py) (3 globals: config, orch_adapter, DRY_RUN)

**Impact:** 22 consumer files across the ma_helper package

---

## Current State

### env.py Globals (11 variables)

Located in [ma_helper/core/env.py](../../ma_helper/core/env.py):

1. **ROOT** (Path)

   - Purpose: Base repo root directory
   - Default: `Path(__file__).resolve().parents[2]`
   - Mutated by: `apply_config()` if `cfg.root` is set, `--root` CLI flag

2. **STATE_HOME** (Path)

   - Purpose: User-level state directory for config and tour progress
   - Default: `$MA_HELPER_HOME` or `~/.ma_helper`
   - Mutated by: `apply_config()` if `cfg.state_dir` is set

3. **CACHE_DIR** (Path)

   - Purpose: Cache directory for build artifacts and results
   - Default: `ROOT / ".ma_cache"`
   - Mutated by: `apply_config()` if `cfg.cache_dir` is set

4. **CACHE_FILE** (Path)

   - Purpose: JSON cache file for persistent caching
   - Default: `CACHE_DIR / "cache.json"`
   - Mutated by: `apply_config()` when CACHE_DIR changes

5. **LAST_RESULTS_FILE** (Path)

   - Purpose: JSON file storing last test/command results
   - Default: `CACHE_DIR / "last_results.json"`
   - Mutated by: `apply_config()` when CACHE_DIR changes

6. **ARTIFACT_DIR** (Path)

   - Purpose: Directory for build artifacts and outputs
   - Default: `CACHE_DIR / "artifacts"`
   - Mutated by: `apply_config()` when CACHE_DIR changes

7. **LOG_DIR** (Path)

   - Purpose: Directory for log files
   - Default: `STATE_HOME / "logs"`
   - Mutated by: `apply_config()` when STATE_HOME changes

8. **LOG_FILE** (Path)

   - Purpose: Main application log file
   - Default: `$MA_LOG_FILE` or `LOG_DIR / "ma.log"`
   - Mutated by: `apply_config()`, environment variable overrides, set to None if `MA_HELPER_NO_WRITE=1`

9. **TELEMETRY_FILE** (Path)

   - Purpose: Telemetry event log file
   - Default: `$MA_TELEMETRY_FILE` or LOG_FILE
   - Mutated by: `apply_config()`, environment variable overrides, set to None if `MA_HELPER_NO_WRITE=1`

10. **FAVORITES_PATH** (Path)

    - Purpose: User preferences JSON (favorites, history, guard level, theme)
    - Default: `STATE_HOME / "config.json"`
    - Mutated by: `apply_config()` when STATE_HOME changes

11. **CACHE_ENABLED** (bool)
    - Purpose: Whether caching/writing is enabled
    - Default: `$MA_HELPER_NO_WRITE != "1"`
    - Mutated by: `apply_config()` always re-checks environment variable

### apply_config() Function

Located in [ma_helper/core/env.py:28-55](../../ma_helper/core/env.py#L28-L55):

**Purpose:** Mutates all 11 global variables based on a HelperConfig object

**Mutation strategy:**

1. Updates ROOT if `cfg.root` is set
2. Updates CACHE_DIR and all derived paths (CACHE_FILE, LAST_RESULTS_FILE, ARTIFACT_DIR) if `cfg.cache_dir` is set
3. Updates STATE_HOME and derived paths (LOG_DIR, FAVORITES_PATH) if `cfg.state_dir` is set
4. Updates LOG_FILE if `cfg.log_file` is set
5. Updates TELEMETRY_FILE if `cfg.telemetry_file` is set
6. Environment variable overrides (`MA_LOG_FILE`, `MA_TELEMETRY_FILE`) always win
7. If `MA_HELPER_NO_WRITE=1`, sets LOG_FILE and TELEMETRY_FILE to None

**Critical issue:** Uses `global` statement to modify all 11 variables at module level

### cli_app.py Globals (3 variables)

Located in [ma_helper/cli_app.py](../../ma_helper/cli_app.py):

1. **DRY_RUN** (bool)

   - Purpose: Global dry-run mode flag
   - Default: False
   - Mutated by: `main()` at line 169-170 based on `--dry-run` flag
   - Location: [cli_app.py:69](../../ma_helper/cli_app.py#L69)

2. **config** (HelperConfig)

   - Purpose: Application configuration object
   - Default: Loaded from ROOT via `HelperConfig.load(ROOT_ACTUAL)`
   - Mutated by: `main()` at lines 118-123 when `--root` flag is provided
   - Location: [cli_app.py:73](../../ma_helper/cli_app.py#L73)

3. **orch_adapter** (Orchestrator adapter instance)
   - Purpose: Task orchestrator adapter (ma_orchestrator or nx)
   - Default: Factory created from `config.adapter`
   - Mutated by: `main()` at line 123 when `--root` flag is provided
   - Location: [cli_app.py:76](../../ma_helper/cli_app.py#L76)

### --root Flag Mutation Flow

When user passes `--root /some/path`:

1. [cli_app.py:117-123](../../ma_helper/cli_app.py#L117-L123): Detects `args.root`
2. Sets `env.ROOT = Path(args.root).resolve()`
3. Reloads `config = HelperConfig.load(env.ROOT)`
4. Calls `env.apply_config(config)` - mutates all 11 env.py globals
5. Recreates `orch_adapter = adapter_factory(config.root)`

**Problem:** This causes a cascading global mutation affecting all downstream code

---

## Consumer Files

### Direct env.py Consumers (22 files)

Files that import from [ma_helper/core/env.py](../../ma_helper/core/env.py):

1. [ma_helper/core/python.py:7](../../ma_helper/core/python.py#L7) - `from ma_helper.core import env`

   - Uses: `env.ROOT`

2. [ma_helper/tui/app.py:20](../../ma_helper/tui/app.py#L20) - `from ma_helper.core.env import STATE_HOME`

   - Uses: `STATE_HOME`

3. [ma_helper/adapters/orchestrator_ma.py:10](../../ma_helper/adapters/orchestrator_ma.py#L10) - `from ma_helper.core.env import ROOT`

   - Uses: `ROOT`

4. [ma_helper/commands/system.py:10](../../ma_helper/commands/system.py#L10) - `from ma_helper.core.env import ROOT`

   - Uses: `ROOT`

5. [ma_helper/commands/registry_cmds.py:12](../../ma_helper/commands/registry_cmds.py#L12) - `from ma_helper.core.env import ROOT`

   - Uses: `ROOT`

6. [ma_helper/commands/helpdesk.py:12](../../ma_helper/commands/helpdesk.py#L12) - `from ma_helper.core.env import ROOT, STATE_HOME, CACHE_ENABLED`

   - Uses: `ROOT`, `STATE_HOME`, `CACHE_ENABLED`

7. [ma_helper/commands/gitflow.py:9](../../ma_helper/commands/gitflow.py#L9) - `from ma_helper.core.env import ROOT`

   - Uses: `ROOT`

8. [ma_helper/commands/gitops.py:8](../../ma_helper/commands/gitops.py#L8) - `from ma_helper.core.env import ROOT`

   - Uses: `ROOT`

9. [ma_helper/commands/dispatch.py:14](../../ma_helper/commands/dispatch.py#L14) - `from ma_helper.core.env import ROOT`

   - Uses: `ROOT`

10. [ma_helper/commands/taskgraph.py:12](../../ma_helper/commands/taskgraph.py#L12) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

11. [ma_helper/commands/runtime.py:8](../../ma_helper/commands/runtime.py#L8) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

12. [ma_helper/commands/chatdev.py:7](../../ma_helper/commands/chatdev.py#L7) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

13. [ma_helper/commands/favorites.py:10](../../ma_helper/commands/favorites.py#L10) - `from ma_helper.core.env import ARTIFACT_DIR`

    - Uses: `ARTIFACT_DIR`
    - Also imports `ROOT` locally at line 34

14. [ma_helper/commands/tooling.py:9](../../ma_helper/commands/tooling.py#L9) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

15. [ma_helper/commands/visual.py:9](../../ma_helper/commands/visual.py#L9) - `from ma_helper.core.env import CACHE_DIR, LAST_RESULTS_FILE, ROOT`

    - Uses: `CACHE_DIR`, `LAST_RESULTS_FILE`, `ROOT`

16. [ma_helper/commands/scaffold.py:9](../../ma_helper/commands/scaffold.py#L9) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

17. [ma_helper/commands/watch.py:10](../../ma_helper/commands/watch.py#L10) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

18. [ma_helper/commands/testflow.py:16](../../ma_helper/commands/testflow.py#L16) - `from ma_helper.core.env import ROOT, STATE_HOME`

    - Uses: `ROOT`, `STATE_HOME`

19. [ma_helper/commands/ux.py:9](../../ma_helper/commands/ux.py#L9) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

20. [ma_helper/commands/system_ops.py:11](../../ma_helper/commands/system_ops.py#L11) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

21. [ma_helper/commands/smoke.py:8](../../ma_helper/commands/smoke.py#L8) - `from ma_helper.core.env import ROOT`

    - Uses: `ROOT`

22. [ma_helper/cli_app.py:60](../../ma_helper/cli_app.py#L60) - `from ma_helper.core import env`
    - Uses: All globals, calls `env.apply_config()`, mutates `env.ROOT`
    - Also imports specific globals at line 335: `LAST_RESULTS_FILE`, `LOG_FILE`

### Direct cli_app.py Consumers (1 file)

1. [ma_helper/cli.py:5](../../ma_helper/cli.py#L5) - Comment only, no actual import

**Note:** cli_app.py is the main entry point, so its globals are self-contained

### Usage Patterns

**Pattern 1: ROOT-only consumers (18 files)**
Most files only need `ROOT` to resolve repo-relative paths.

**Pattern 2: Multi-path consumers (4 files)**

- visual.py: needs CACHE_DIR, LAST_RESULTS_FILE, ROOT
- helpdesk.py: needs ROOT, STATE_HOME, CACHE_ENABLED
- testflow.py: needs ROOT, STATE_HOME
- favorites.py: needs ARTIFACT_DIR (derived from CACHE_DIR)

**Pattern 3: Full env module import (2 files)**

- python.py: imports `env` module, uses `env.ROOT`
- cli_app.py: imports `env` module, uses all globals and mutates them

---

## Proposed Design

### RuntimeConfig Dataclass

Replace mutable globals with an immutable frozen dataclass:

```python
# ma_helper/core/config.py (extend existing HelperConfig)

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    """Immutable runtime configuration computed from HelperConfig and environment.

    This replaces the mutable globals in ma_helper.core.env.
    """
    # Core paths
    root: Path
    state_home: Path

    # Cache paths
    cache_dir: Path
    cache_file: Path
    last_results_file: Path
    artifact_dir: Path

    # Log paths
    log_dir: Path
    log_file: Path | None
    telemetry_file: Path | None

    # User state
    favorites_path: Path

    # Flags
    cache_enabled: bool

    @classmethod
    def from_helper_config(cls, cfg: HelperConfig) -> "RuntimeConfig":
        """Create RuntimeConfig from HelperConfig, applying environment overrides.

        This replaces the env.apply_config() mutation pattern.
        """
        import os

        # Compute state_home
        state_home = cfg.state_dir or Path(os.environ.get(
            "MA_HELPER_HOME",
            Path.home() / ".ma_helper"
        ))

        # Compute cache_dir and derived paths
        cache_dir = cfg.cache_dir or (cfg.root / ".ma_cache")
        cache_file = cache_dir / "cache.json"
        last_results_file = cache_dir / "last_results.json"
        artifact_dir = cache_dir / "artifacts"

        # Compute log paths
        log_dir = state_home / "logs"
        log_file = cfg.log_file or (log_dir / "ma.log")
        telemetry_file = cfg.telemetry_file or log_file

        # Environment variable overrides
        if os.environ.get("MA_LOG_FILE"):
            log_file = Path(os.environ["MA_LOG_FILE"])
        if os.environ.get("MA_TELEMETRY_FILE"):
            telemetry_file = Path(os.environ["MA_TELEMETRY_FILE"])

        # Check cache enabled
        cache_enabled = os.environ.get("MA_HELPER_NO_WRITE") != "1"
        if not cache_enabled:
            log_file = None
            telemetry_file = None

        favorites_path = state_home / "config.json"

        return cls(
            root=cfg.root,
            state_home=state_home,
            cache_dir=cache_dir,
            cache_file=cache_file,
            last_results_file=last_results_file,
            artifact_dir=artifact_dir,
            log_dir=log_dir,
            log_file=log_file,
            telemetry_file=telemetry_file,
            favorites_path=favorites_path,
            cache_enabled=cache_enabled,
        )
```

### DRY_RUN Flag Handling

Options for DRY_RUN:

**Option A: Add to RuntimeConfig**

```python
@dataclass(frozen=True)
class RuntimeConfig:
    # ... existing fields ...
    dry_run: bool = False
```

**Option B: Pass as parameter to functions that need it**

- More explicit
- Avoids mixing runtime flags with path configuration
- **Recommended approach**

### Adapter Management

The `orch_adapter` global should become a field on RuntimeConfig or be managed separately:

**Option A: Include adapter in RuntimeConfig**

```python
@dataclass(frozen=True)
class RuntimeConfig:
    # ... existing fields ...
    adapter: Any  # The orchestrator adapter instance
```

**Option B: Create adapter on-demand (recommended)**

```python
# In cli_app.py
def main(argv=None) -> int:
    # ... parse args ...
    config = HelperConfig.load(root)
    runtime = RuntimeConfig.from_helper_config(config)
    adapter = get_orch_adapter(config.adapter)(runtime.root)

    # Pass runtime and adapter to commands
    return _dispatch(args, runtime, adapter, ...)
```

---

## Migration Steps

### Phase 1: Create RuntimeConfig (No Breaking Changes)

**Task 32: Create RuntimeConfig dataclass**

- Add `RuntimeConfig` to [ma_helper/core/config.py](../../ma_helper/core/config.py)
- Add `from_helper_config()` class method
- Add unit tests verifying environment variable handling
- No changes to existing code yet

### Phase 2: Update env.py (Parallel System)

**Task 33: Add RuntimeConfig support to env.py**

- Keep existing globals for backward compatibility
- Add `_runtime_config: RuntimeConfig | None = None`
- Add `set_runtime_config(cfg: RuntimeConfig)` function
- Update `apply_config()` to also set `_runtime_config`
- Add getter functions that prefer `_runtime_config` if set:
  ```python
  def get_root() -> Path:
      return _runtime_config.root if _runtime_config else ROOT
  ```

### Phase 3: Update cli_app.py Entry Point

**Task 34: Use RuntimeConfig in cli_app.py**

- Remove global `config`, `orch_adapter` mutations
- Create `RuntimeConfig` at the start of `main()`
- Recreate `RuntimeConfig` if `--root` is provided
- Pass `runtime` and `adapter` to `_dispatch()`
- Update all command handlers to accept `runtime` parameter

### Phase 4: Migrate Consumers (22 files)

**Task 35-56: Update each consumer file**

For each of the 22 consumer files:

1. Change imports from `from ma_helper.core.env import X` to accept `runtime: RuntimeConfig` parameter
2. Update function signatures to accept `runtime: RuntimeConfig`
3. Replace `ROOT` → `runtime.root`, `CACHE_DIR` → `runtime.cache_dir`, etc.
4. Thread `runtime` parameter through call chains

**Migration order (by complexity):**

**Batch 1: Single ROOT users (18 files) - Low risk**

- python.py, system.py, registry_cmds.py, gitflow.py, gitops.py
- dispatch.py, taskgraph.py, runtime.py, chatdev.py, tooling.py
- scaffold.py, watch.py, ux.py, system_ops.py, smoke.py
- orchestrator_ma.py (adapter)

**Batch 2: Multi-path users (4 files) - Medium risk**

- visual.py (CACHE_DIR, LAST_RESULTS_FILE, ROOT)
- helpdesk.py (ROOT, STATE_HOME, CACHE_ENABLED)
- testflow.py (ROOT, STATE_HOME)
- favorites.py (ARTIFACT_DIR)

**Batch 3: state.py special handling**

- Currently uses `FAVORITES_PATH`, `LOG_FILE` as default parameters
- Change to require `runtime` parameter or accept optional override paths

**Batch 4: tui/app.py**

- Update HelperTUI to accept `runtime: RuntimeConfig`

### Phase 5: Remove Legacy Globals

**Task 57: Remove mutable globals**

- Remove all 11 global variables from [ma_helper/core/env.py](../../ma_helper/core/env.py)
- Remove `apply_config()` function
- Remove `DRY_RUN` global from [ma_helper/cli_app.py](../../ma_helper/cli_app.py)
- Keep only helper functions if needed (e.g., discover_root)

### Phase 6: Update Tests

**Task 58: Fix test suite**

- Update all tests that mock env.py globals
- Change to mock RuntimeConfig or pass test configs
- Verify 100% test pass rate

---

## Risk Assessment

### High Risk Areas

1. **state.py functions** (load_favorites, save_favorites)

   - Currently use `FAVORITES_PATH` and `LOG_FILE` as default parameter values
   - These are evaluated at import time, not call time
   - **Solution:** Change to accept `runtime: RuntimeConfig` or optional path overrides

2. **Partial application in cli_app.py**

   - Lines 80-81 use `partial()` to bind `env.TELEMETRY_FILE`
   - This captures the value at module load time
   - **Solution:** Recreate partials in `main()` after RuntimeConfig is created

3. **Dynamic --root flag**
   - Currently mutates globals mid-execution
   - **Solution:** Recreate RuntimeConfig and adapter, pass new instances down

### Medium Risk Areas

1. **Adapter factories**

   - Adapters currently import `ROOT` directly
   - **Solution:** Pass `runtime.root` to adapter constructors

2. **Command handler signatures**
   - 22 files need signature updates
   - **Solution:** Gradual migration with temporary backward compatibility

### Low Risk Areas

1. **Simple ROOT consumers**
   - Most files only use `ROOT` for path resolution
   - Straightforward parameter threading

---

## Testing Strategy

### Unit Tests

1. **RuntimeConfig.from_helper_config()**

   - Test default path computation
   - Test environment variable overrides (`MA_LOG_FILE`, `MA_TELEMETRY_FILE`, `MA_HELPER_NO_WRITE`)
   - Test cache_enabled logic
   - Test path absolutization

2. **Immutability**
   - Verify frozen dataclass prevents mutation
   - Verify no global state changes

### Integration Tests

1. **--root flag**

   - Test that `--root /new/path` creates new RuntimeConfig
   - Verify all derived paths use new root
   - Verify adapter is recreated with new root

2. **Environment variable overrides**
   - Test `MA_HELPER_NO_WRITE=1` disables logging
   - Test `MA_LOG_FILE` override
   - Test `MA_TELEMETRY_FILE` override

### Regression Tests

1. **Existing test suite**
   - Run full test suite after each batch migration
   - Ensure 100% pass rate maintained

---

## Success Criteria

- [ ] All 11 env.py globals eliminated
- [ ] All 3 cli_app.py globals eliminated (config, orch_adapter, DRY_RUN)
- [ ] RuntimeConfig is immutable (frozen dataclass)
- [ ] No `global` statements remain
- [ ] All 22 consumer files updated
- [ ] All tests pass (100% pass rate)
- [ ] No runtime mutations of config state
- [ ] `--root` flag works correctly with new system

---

## Implementation Estimates

- **Phase 1** (RuntimeConfig creation): 1 task
- **Phase 2** (env.py parallel support): 1 task
- **Phase 3** (cli_app.py update): 1 task
- **Phase 4** (Consumer migration): 22 tasks (can be parallelized in batches)
- **Phase 5** (Legacy removal): 1 task
- **Phase 6** (Test updates): 1 task

**Total: 27 tasks**

---

## Related Documentation

- [GLOBAL_STATE_AUDIT.md](GLOBAL_STATE_AUDIT.md) - Priority 2: Config Object Migration
- [REPO_ANALYSIS_2026Q1.md](REPO_ANALYSIS_2026Q1.md) - Main audit document
- [ma_helper/core/env.py](../../ma_helper/core/env.py) - Current global state
- [ma_helper/cli_app.py](../../ma_helper/cli_app.py) - Entry point with globals
- [ma_helper/core/config.py](../../ma_helper/core/config.py) - HelperConfig dataclass

---

## Next Steps

After this analysis is approved:

1. Proceed with **Task 32**: Create RuntimeConfig dataclass
2. Write unit tests for RuntimeConfig.from_helper_config()
3. Begin Phase 2: Add parallel RuntimeConfig support to env.py
4. Migrate consumers in batches (starting with simple ROOT-only files)
5. Complete with legacy cleanup and test verification
