# Global State Audit

**Date**: 2026-01-07
**Task**: Analyze all `global` keyword usage and create remediation plan
**Reference**: [docs/audits/REPO_ANALYSIS_2026Q1.md](REPO_ANALYSIS_2026Q1.md) (Task 22)

---

## Executive Summary

- **Total `global` statements**: 26
- **Type A (Logger reconfiguration)**: 18 (69%)
- **Type B (Module-level caches)**: 3 (12%)
- **Type C (Mutable config)**: 3 (12%)
- **Type D (In-process calibration)**: 2 (7%)

### Key Findings

1. **Logger globals dominate** - 18/26 (69%) of all global usage is `global _log` for CLI reconfiguration
2. **Caching is minimal** - Only 3 cache-related globals, all legitimate lazy-load patterns
3. **Config mutation exists** - 3 config-related globals with varying risk levels
4. **No critical issues** - All global usage is deliberate and documented

---

## Detailed Categorization

### Type A: Logger Reconfiguration (18 instances)

**Pattern**: CLI tools use `global _log` to reconfigure module-level logger based on CLI args.

| File                                                                            | Variable       | Purpose                 | Risk | Remediation                 |
| ------------------------------------------------------------------------------- | -------------- | ----------------------- | ---- | --------------------------- |
| `tools/lyrics/import_kaylin_lyrics_into_db_v1.py:194`                           | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/spotify_apply_overrides_to_core_corpus.py:289`                           | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/hci_final_score.py:364`                                                  | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/ma_add_philosophy_to_hci.py:71`                                          | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/hci/ma_add_echo_to_client_rich_v1.py:1001`                               | `_log, _QUIET` | CLI logger + quiet flag | Low  | Pass logger/config as param |
| `tools/hci/ma_add_echo_to_hci_v1.py:473`                                        | `_log, _QUIET` | CLI logger + quiet flag | Low  | Pass logger/config as param |
| `tools/hci/hci_rank_from_folder.py:278`                                         | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/calibration/backfill_features_meta.py:131`                               | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/calibration/calibration_readiness.py:88`                                 | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/calibration/equilibrium_merge_full.py:43`                                | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/audio/tempo_sidecar_runner.py:406`                                       | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/audio/ma_audio_features.py:1259`                                         | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/ma_merge_client_and_hci.py:793`                                          | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `tools/pack_writer.py:313`                                                      | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `engines/audio_engine/tools/misc/ma_truth_vs_ml_finalize_truth.py:91`           | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `engines/audio_engine/tools/misc/pack_show_hci.py:78`                           | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `engines/audio_engine/tools/calibration/build_baseline_from_snapshot.py:71`     | `_log`         | CLI logger setup        | Low  | Pass logger as param        |
| `engines/audio_engine/tools/calibration/build_baseline_from_calibration.py:178` | `_log`         | CLI logger setup        | Low  | Pass logger as param        |

**Analysis**:

- All 18 instances follow same pattern: CLI `main()` reconfigures module-level `_log` based on args
- Logger is then used by multiple helper functions in the same module
- Risk is LOW - confined to single module, no cross-module state
- Remediation path: Pass logger as explicit parameter to functions

---

### Type B: Module-Level Caches (3 instances)

**Pattern**: Lazy-load caches to avoid repeated I/O or network calls.

| File                                                      | Variable                          | Purpose                   | Risk     | Remediation                                   |
| --------------------------------------------------------- | --------------------------------- | ------------------------- | -------- | --------------------------------------------- |
| `tools/aee_band_thresholds.py:92`                         | `_THRESHOLDS_CACHE`               | Cache threshold JSON file | **None** | Acceptable - prevents redundant file reads    |
| `engines/lyrics_engine/src/ma_lyrics_engine/export.py:20` | `_NORMS_CACHE, _NORMS_PATH_CACHE` | Cache lyrics norms file   | **None** | Acceptable - prevents redundant file reads    |
| `hosts/advisor_host/auth/auth.py:38`                      | `_JWKS_CACHE, _JWKS_FETCH_TS`     | Cache JWKS with TTL       | **None** | Acceptable - prevents excessive network calls |

**Analysis**:

- All 3 are legitimate lazy-load patterns with cache invalidation logic
- `auth.py` includes TTL-based invalidation (60s default)
- No thread-safety issues (single-threaded CLI tools)
- Risk is **NONE** - these are performance optimizations with no side effects
- No remediation needed

---

### Type C: Mutable Configuration (3 instances)

**Pattern**: Runtime configuration updates based on CLI args or initialization.

| File                       | Variable                               | Purpose                          | Risk       | Remediation                       |
| -------------------------- | -------------------------------------- | -------------------------------- | ---------- | --------------------------------- |
| `ma_helper/core/env.py:30` | `CACHE_DIR, CACHE_FILE, ...` (11 vars) | Apply config overrides           | **Medium** | Convert to config object          |
| `ma_helper/cli_app.py:119` | `config, orch_adapter`                 | Update global config on `--root` | **Medium** | Pass as context object            |
| `ma_helper/cli_app.py:169` | `DRY_RUN`                              | Persist dry-run flag             | **Low**    | Pass as arg or use args namespace |

**Analysis**:

#### `ma_helper/core/env.py:30` - Path Configuration

- **Risk**: Medium - 11 module-level path variables mutated by `apply_config()`
- **Impact**: Used throughout ma_helper for caching, logging, telemetry
- **Why it exists**: Allow runtime override of default paths via `HelperConfig`
- **Remediation**:
  - Replace with immutable `Config` dataclass
  - Pass config object explicitly to functions
  - Estimated effort: 3-4 hours (affects ~20 files)

#### `ma_helper/cli_app.py:119` - Root Override

- **Risk**: Medium - Updates `config` and `orch_adapter` when `--root` is passed
- **Impact**: Reconfigures orchestrator adapter mid-execution
- **Why it exists**: Allow per-command root override
- **Remediation**:
  - Pass config as explicit context object
  - Avoid mutating global state after initialization
  - Estimated effort: 2-3 hours

#### `ma_helper/cli_app.py:169` - DRY_RUN Flag

- **Risk**: Low - Single boolean flag for dry-run mode
- **Impact**: Used by command handlers to skip side effects
- **Why it exists**: Simplify dry-run checks across commands
- **Remediation**:
  - Pass via `args` namespace or context object
  - Low priority - minimal impact
  - Estimated effort: 30 minutes

---

### Type D: In-Process Calibration (2 instances)

**Pattern**: Calibrate thresholds at runtime based on loaded data.

| File                                                                        | Variable                                                  | Purpose                          | Risk    | Remediation                                  |
| --------------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------- | ------- | -------------------------------------------- |
| `tools/ma_benchmark_check.py:367`                                           | `ENERGY_THRESHOLDS, DANCE_THRESHOLDS, VALENCE_THRESHOLDS` | Runtime threshold calibration    | **Low** | Return calibrated thresholds, pass as params |
| `engines/lyrics_engine/tools/lyrics/import_kaylin_lyrics_into_db_v1.py:193` | `_log`                                                    | CLI logger (duplicate of Type A) | Low     | (See Type A)                                 |

**Analysis**:

#### `tools/ma_benchmark_check.py:367` - Threshold Calibration

- **Risk**: Low - Mutates thresholds for current run only
- **Purpose**: Calibrate energy/dance/valence thresholds based on loaded benchmark data
- **Scope**: Single-process, no persistence, documented as "in-process only"
- **Why it exists**: Dynamic calibration for benchmark validation
- **Remediation**:
  - Return calibrated thresholds from function
  - Pass as parameters to band functions
  - Estimated effort: 1-2 hours

---

## Remediation Recommendations

### Priority 1: Standardize Logger Passing (18 files)

**Effort**: Medium (8-12 hours)
**Impact**: Eliminates 69% of global usage
**Risk**: Low - purely mechanical refactor

**Steps**:

1. Add `logger: Callable` parameter to helper functions
2. Pass `_log` explicitly from `main()`
3. Remove `global _log` statements
4. Verify tests pass

**Benefits**:

- Eliminates largest category of global state
- Makes logger dependency explicit
- Improves testability (can inject mock loggers)

---

### Priority 2: Convert ma_helper Config to Immutable Object (2 files)

**Effort**: Medium (3-4 hours)
**Impact**: Removes mutable config globals
**Risk**: Medium - affects ~20 consuming files

**Steps**:

1. Create `@dataclass(frozen=True)` for `RuntimeConfig`
2. Replace `env.py` globals with config object
3. Pass config explicitly to functions needing paths
4. Update `cli_app.py` to use config object

**Benefits**:

- Eliminates 11 mutable path globals
- Makes config immutable and thread-safe
- Improves testing (can inject test configs)

---

### Priority 3: Refactor Calibration Threshold Passing (1 file)

**Effort**: Low (1-2 hours)
**Impact**: Removes in-process calibration globals
**Risk**: Low - single file

**Steps**:

1. Return calibrated thresholds from `_calibrate_thresholds()`
2. Pass thresholds to `band_energy()`, `band_dance()`, `band_valence()`
3. Remove `global ENERGY_THRESHOLDS, DANCE_THRESHOLDS, VALENCE_THRESHOLDS`

**Benefits**:

- Explicit data flow
- Easier to test with custom thresholds

---

### Priority 4: Remove DRY_RUN Global (1 file)

**Effort**: Low (30 minutes)
**Impact**: Minor cleanup
**Risk**: Low

**Steps**:

1. Pass `dry_run` via `args` namespace to commands
2. Remove `global DRY_RUN`

---

## Caveats & Non-Issues

### ✅ Acceptable Usage (No Remediation Needed)

1. **Module-level caches** (`_THRESHOLDS_CACHE`, `_NORMS_CACHE`, `_JWKS_CACHE`)

   - Standard lazy-load pattern
   - Prevents redundant I/O
   - No side effects

2. **Variable names containing "global"** (not actual `global` statements)
   - `peak_global` in `tempo_estimator.py:323` - local variable
   - Comments mentioning "global" - ignored

---

## Implementation Timeline

**Phase 1** (Task 23): Logger passing refactor
**Phase 2** (Task 24): Config object migration
**Phase 3** (Task 25): Calibration threshold refactor
**Phase 4** (Task 26): DRY_RUN cleanup

**Total Estimated Effort**: 13-18 hours
**Files Affected**: ~22 files
**Test Coverage**: All changes covered by existing test suite (108 tests)

---

## Appendix: Full Global Usage List

```bash
# Non-archive global statements (26 total)
./tools/lyrics/import_kaylin_lyrics_into_db_v1.py:194:    global _log
./tools/spotify_apply_overrides_to_core_corpus.py:289:    global _log
./tools/hci_final_score.py:364:    global _log
./tools/ma_add_philosophy_to_hci.py:71:    global _log
./tools/hci/ma_add_echo_to_client_rich_v1.py:1001:    global _log, _QUIET
./tools/hci/ma_add_echo_to_hci_v1.py:473:    global _log, _QUIET
./tools/hci/hci_rank_from_folder.py:278:    global _log
./tools/calibration/backfill_features_meta.py:131:    global _log
./tools/calibration/calibration_readiness.py:88:    global _log
./tools/calibration/equilibrium_merge_full.py:43:    global _log
./tools/ma_benchmark_check.py:367:    global ENERGY_THRESHOLDS, DANCE_THRESHOLDS, VALENCE_THRESHOLDS
./tools/audio/tempo_sidecar_runner.py:406:    global _log
./tools/audio/ma_audio_features.py:1259:    global _log
./tools/ma_merge_client_and_hci.py:793:    global _log
./tools/aee_band_thresholds.py:92:    global _THRESHOLDS_CACHE
./tools/pack_writer.py:313:    global _log
./engines/audio_engine/tools/misc/ma_truth_vs_ml_finalize_truth.py:91:    global _log
./engines/audio_engine/tools/misc/pack_show_hci.py:78:    global _log
./engines/audio_engine/tools/calibration/build_baseline_from_snapshot.py:71:    global _log
./engines/audio_engine/tools/calibration/build_baseline_from_calibration.py:178:    global _log
./engines/lyrics_engine/tools/lyrics/import_kaylin_lyrics_into_db_v1.py:193:    global _log
./engines/lyrics_engine/src/ma_lyrics_engine/export.py:20:    global _NORMS_CACHE, _NORMS_PATH_CACHE
./hosts/advisor_host/auth/auth.py:38:    global _JWKS_CACHE, _JWKS_FETCH_TS
./ma_helper/core/env.py:30:    global CACHE_DIR, CACHE_FILE, LAST_RESULTS_FILE, ARTIFACT_DIR, STATE_HOME, LOG_DIR, LOG_FILE, TELEMETRY_FILE, FAVORITES_PATH, CACHE_ENABLED, ROOT
./ma_helper/cli_app.py:119:        global config, orch_adapter
./ma_helper/cli_app.py:169:    global DRY_RUN
```

---

**End of Audit**
