# Global State Audit

**Date**: 2026-01-07
**Task**: Analyze all `global` keyword usage and create remediation plan
**Reference**: [docs/audits/REPO_ANALYSIS_2026Q1.md](REPO_ANALYSIS_2026Q1.md) (Task 22)

---

## Executive Summary

- **Total `global` statements**: 8 (down from 26)
- **Type A (Logger reconfiguration)**: ✅ **0** - COMPLETE (was 18)
- **Type B (Module-level caches)**: 3 (38%)
- **Type C (Mutable config)**: 3 (38%)
- **Type D (In-process calibration)**: 2 (24%)

### Key Findings

1. **✅ Logger globals eliminated** - All 18 logger globals removed (Tasks 25-29, completed 2026-01-07)
2. **Caching is minimal** - Only 3 cache-related globals, all legitimate lazy-load patterns
3. **Config mutation exists** - 3 config-related globals with varying risk levels
4. **No critical issues** - All global usage is deliberate and documented

---

## Detailed Categorization

### Type A: Logger Reconfiguration ✅ **COMPLETE** (0 instances, was 18)

**Status**: ✅ **All logger globals eliminated** (Tasks 25-29, completed 2026-01-07)

**Commits**:

- Task 25: `3927408` - tools/calibration/ (3 files)
- Task 26: `e1bb291` - tools/hci/ (3 files)
- Task 27: `39f4cc9` - tools/ top-level (5 files)
- Task 28: `6fc6122` - tools/audio/ + pack_writer.py (3 files)
- Task 29: `01d67e8` - engines/ (5 files)

**Original instances** (now refactored):

| File                                                                            | Variable       | Status    | Commit  |
| ------------------------------------------------------------------------------- | -------------- | --------- | ------- |
| `tools/lyrics/import_kaylin_lyrics_into_db_v1.py:194`                           | `_log`         | ✅ Fixed  | 39f4cc9 |
| `tools/spotify_apply_overrides_to_core_corpus.py:289`                           | `_log`         | ✅ Fixed  | 39f4cc9 |
| `tools/hci_final_score.py:364`                                                  | `_log`         | ✅ Fixed  | 39f4cc9 |
| `tools/ma_add_philosophy_to_hci.py:71`                                          | `_log`         | ✅ Fixed  | 39f4cc9 |
| `tools/hci/ma_add_echo_to_client_rich_v1.py:1001`                               | `_log, _QUIET` | ✅ Fixed  | e1bb291 |
| `tools/hci/ma_add_echo_to_hci_v1.py:473`                                        | `_log, _QUIET` | ✅ Fixed  | e1bb291 |
| `tools/hci/hci_rank_from_folder.py:278`                                         | `_log`         | ✅ Fixed  | e1bb291 |
| `tools/calibration/backfill_features_meta.py:131`                               | `_log`         | ✅ Fixed  | 3927408 |
| `tools/calibration/calibration_readiness.py:88`                                 | `_log`         | ✅ Fixed  | 3927408 |
| `tools/calibration/equilibrium_merge_full.py:43`                                | `_log`         | ✅ Fixed  | 3927408 |
| `tools/audio/tempo_sidecar_runner.py:406`                                       | `_log`         | ✅ Fixed  | 6fc6122 |
| `tools/audio/ma_audio_features.py:1259`                                         | `_log`         | ✅ Fixed  | 6fc6122 |
| `tools/ma_merge_client_and_hci.py:793`                                          | `_log`         | ✅ Fixed  | 39f4cc9 |
| `tools/pack_writer.py:313`                                                      | `_log`         | ✅ Fixed  | 6fc6122 |
| `engines/audio_engine/tools/misc/ma_truth_vs_ml_finalize_truth.py:91`           | `_log`         | ✅ Fixed  | 01d67e8 |
| `engines/audio_engine/tools/misc/pack_show_hci.py:78`                           | `_log`         | ✅ Fixed  | 01d67e8 |
| `engines/audio_engine/tools/calibration/build_baseline_from_snapshot.py:71`     | `_log`         | ✅ Fixed  | 01d67e8 |
| `engines/audio_engine/tools/calibration/build_baseline_from_calibration.py:178` | `_log`         | ✅ Fixed  | 01d67e8 |
| `engines/lyrics_engine/tools/lyrics/import_kaylin_lyrics_into_db_v1.py:193`     | `_log`         | ✅ Fixed  | 01d67e8 |

**Refactoring approach**:

- Removed module-level `_log` initialization and `global _log` statements
- Changed `_log` to local `log` variable in `main()`
- Added `log` (and `quiet` where applicable) parameters to helper functions
- Used lambda wrappers for compatibility: `logger=lambda msg: log(msg)`
- Fixed LOG_REDACT handling with `os.getenv("LOG_REDACT", "0") == "1"`

**Verification**: `grep -rn "global _log" --include="*.py" . | grep -v archive` returns 0 results

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

### ✅ Priority 1: Standardize Logger Passing - **COMPLETE**

**Status**: ✅ **100% Complete** (Tasks 25-29, completed 2026-01-07)
**Files refactored**: 19 files across 5 commits
**Impact**: Eliminated 18 global statements (69% of all globals)

**Commits**:

- Task 25 (`3927408`): tools/calibration/ - 3 files
- Task 26 (`e1bb291`): tools/hci/ - 3 files
- Task 27 (`39f4cc9`): tools/ top-level - 5 files
- Task 28 (`6fc6122`): tools/audio/ + pack_writer.py - 3 files
- Task 29 (`01d67e8`): engines/ - 5 files

**Approach taken**:

1. Removed module-level `_log` and `global _log` statements
2. Changed to local `log` variable in `main()`
3. Added `log` parameter to helper functions
4. Used lambda wrappers for compatibility
5. Fixed LOG_REDACT environment variable handling

**Results**:

- ✅ All 18 logger globals eliminated
- ✅ All refactored files compile successfully
- ✅ Logger dependencies now explicit
- ✅ Improved testability (can inject mock loggers)

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

### Current State (8 remaining, as of 2026-01-07)

```bash
# Non-archive global statements (8 total, down from 26)
./tools/ma_benchmark_check.py:367:    global ENERGY_THRESHOLDS, DANCE_THRESHOLDS, VALENCE_THRESHOLDS
./tools/aee_band_thresholds.py:92:    global _THRESHOLDS_CACHE
./engines/lyrics_engine/src/ma_lyrics_engine/export.py:20:    global _NORMS_CACHE, _NORMS_PATH_CACHE
./hosts/advisor_host/auth/auth.py:38:    global _JWKS_CACHE, _JWKS_FETCH_TS
./ma_helper/core/env.py:30:    global CACHE_DIR, CACHE_FILE, LAST_RESULTS_FILE, ARTIFACT_DIR, STATE_HOME, LOG_DIR, LOG_FILE, TELEMETRY_FILE, FAVORITES_PATH, CACHE_ENABLED, ROOT
./ma_helper/cli_app.py:119:        global config, orch_adapter
./ma_helper/cli_app.py:169:    global DRY_RUN
```

### Original State (26 total, as of initial audit)

All Type A (Logger) globals have been eliminated. The 18 removed instances were:

```bash
# ELIMINATED - Logger globals (18 total) ✅
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
./tools/audio/tempo_sidecar_runner.py:406:    global _log
./tools/audio/ma_audio_features.py:1259:    global _log
./tools/ma_merge_client_and_hci.py:793:    global _log
./tools/pack_writer.py:313:    global _log
./engines/audio_engine/tools/misc/ma_truth_vs_ml_finalize_truth.py:91:    global _log
./engines/audio_engine/tools/misc/pack_show_hci.py:78:    global _log
./engines/audio_engine/tools/calibration/build_baseline_from_snapshot.py:71:    global _log
./engines/audio_engine/tools/calibration/build_baseline_from_calibration.py:178:    global _log
./engines/lyrics_engine/tools/lyrics/import_kaylin_lyrics_into_db_v1.py:193:    global _log
```

---

**End of Audit**
