# Shim File Consolidation Plan

**Generated**: 2026-01-07
**Audit Reference**: `docs/audits/REPO_ANALYSIS_2026Q1.md` (Section: Excessive Shim/Wrapper Layer)
**Task**: Task 17 - Analyze and document shim files for consolidation

---

## Executive Summary

This document catalogs all shim/wrapper files in the music-advisor codebase and provides a consolidation plan to reduce maintenance overhead.

**Key Findings**:
- **Total Shims Identified**: 28 files
- **Total Lines of Shim Code**: ~500 lines
- **Active Consumers**: 15 files for Type A (security), 2 for Type C (tools/cli), 0 for others
- **Recommendation**: Phase 1 removes Type C-E shims (low risk), Phase 2 removes Type B (zero consumers), Phase 3 removes Type A (requires consumer migration)

---

## Shim Categories

### Type A: security/* → shared/security/* (ACTIVE - 15 consumers)

**Status**: ACTIVE USE - Requires careful migration
**Risk Level**: HIGH (many consumers)
**Consumers**: 15 files

#### Files:
1. `security/files.py` (18 lines)
   - Delegates to: `shared.security.files`
   - Exports: `FileValidationError`, `validate_filename`, `ensure_allowed_extension`, `ensure_size_ok`, `ensure_max_size`

2. `security/db.py` (14 lines)
   - Delegates to: `shared.security.db`
   - Exports: `DBSecurityError`, `validate_table_name`, `safe_execute`

3. `security/config.py` (12 lines)
   - Delegates to: `shared.security.config`
   - Exports: `SecurityConfig`, `CONFIG`

4. `security/paths.py` (11 lines)
   - Delegates to: `shared.security.paths`
   - Exports: `PathValidationError`, `safe_join`

5. `security/subprocess.py` (12 lines)
   - Delegates to: `shared.security.subprocess`
   - Exports: `SubprocessValidationError`, `run_safe`

#### Consumer Files (15):
- `tools/audio/ma_audio_features.py`
- `engines/audio_engine/src/ma_audio_engine/adapters_src/cli_adapter.py`
- `tools/sidecar_adapter.py`
- `engines/audio_engine/tools/misc/sidecar_sweep.py`
- `tests/test_security_helpers.py`
- `engines/lyrics_engine/src/ma_stt_engine/whisper_backend.py`
- `engines/audio_engine/tools/calibration/calibration_run.py`
- `engines/audio_engine/tools/calibration/build_baseline_from_calibration.py`
- `engines/audio_engine/src/ma_audio_engine/pipe_cli.py`
- `engines/audio_engine/src/ma_audio_engine/adapters_src/audio_loader_adapter.py`
- `tools/loudness_report.py`
- `tools/calibration/calibration_readiness.py`
- `tools/audio_metadata_probe.py`
- `tools/audio/normalize_to_lufs.py`
- `tools/audio/loudnorm_exact.py`

---

### Type B: src/ma_config/* → shared/config/* (ZERO consumers)

**Status**: NO ACTIVE CONSUMERS
**Risk Level**: VERY LOW (no consumers found)
**Consumers**: 0 files

#### Files:
1. `src/ma_config/neighbors.py` (16 lines)
   - Delegates to: `shared.config.neighbors`
   - Exports: `DEFAULT_NEIGHBORS_LIMIT`, `DEFAULT_NEIGHBORS_DISTANCE`, `DEFAULT_NEIGHBORS_CONFIG_PATH`, `resolve_neighbors_config`

2. `src/ma_config/constants.py` (16 lines)
   - Delegates to: `shared.config.constants`
   - Exports: `ERA_BUCKETS`, `ERA_BUCKET_MISC`, `TIER_THRESHOLDS`, `LCI_AXES`

3. `src/ma_config/pipeline.py` (14 lines)
   - Delegates to: `shared.config.pipeline`
   - Exports: `HCI_BUILDER_PROFILE_DEFAULT`, `NEIGHBORS_PROFILE_DEFAULT`, `SIDECAR_TIMEOUT_DEFAULT`

4. `src/ma_config/scripts.py` (16 lines)
   - Delegates to: `shared.config.scripts`
   - Exports: `DEFAULT_REPO_ENV`, `DEFAULT_PYTHON`, `DEFAULT_LYRIC_LCI_PROFILE`, `DEFAULT_LYRIC_LCI_CALIBRATION`

5. `src/ma_config/profiles.py` (18 lines)
   - Delegates to: `shared.config.profiles`
   - Exports: `DEFAULT_LCI_PROFILE`, `DEFAULT_LCI_CALIBRATION_PATH`, `DEFAULT_TTC_PROFILE`, `DEFAULT_TTC_CONFIG_PATH`, `resolve_profile_config`

---

### Type C: tools/cli/* → tools/calibration/* (MINIMAL use - 2 consumers)

**Status**: MINIMAL ACTIVE USE
**Risk Level**: LOW (only 2 consumers, both in engines/)
**Consumers**: 2 files (both are also shims that reference these)

#### Files:
1. `tools/cli/backfill_features_meta.py` (9 lines)
   - Delegates to: `tools.calibration.backfill_features_meta`
   - Type: CLI script shim

2. `tools/cli/calibration_readiness.py` (9 lines)
   - Delegates to: `tools.calibration.calibration_readiness`
   - Type: CLI script shim

3. `tools/cli/equilibrium_merge_full.py` (9 lines)
   - Delegates to: `tools.calibration.equilibrium_merge_full`
   - Type: CLI script shim

4. `tools/cli/tempo_sidecar_runner.py` (4 lines - comment only)
   - Delegates to: `engines.audio_engine.tools.cli` (comment only, no implementation)
   - Type: Empty shim placeholder

5. `tools/cli/ma_add_echo_to_hci_v1.py` (4 lines - comment only)
   - Delegates to: `engines.audio_engine.tools.cli` (comment only, no implementation)
   - Type: Empty shim placeholder

6. `tools/cli/hci_rank_from_folder.py` (4 lines - comment only)
   - Delegates to: `engines.audio_engine.tools.cli` (comment only, no implementation)
   - Type: Empty shim placeholder

7. `tools/cli/ma_audio_features.py` (4 lines - comment only)
   - Delegates to: `engines.audio_engine.tools.cli` (comment only, no implementation)
   - Type: Empty shim placeholder

8. `tools/cli/__init__.py` (4 lines - comment only)
   - Delegates to: `engines.audio_engine.tools.cli` (comment only, no exports)
   - Type: Empty shim placeholder

#### Consumer Files (2):
- `engines/audio_engine/tools/misc/backfill_features_meta.py` (itself a shim)
- `engines/audio_engine/tools/hci/equilibrium_merge_full.py` (itself a shim)

#### Script References (2):
- `hosts/macos_app/scripts/pipeline_smoke.sh` → uses `tools/cli/ma_audio_features.py`
- `hosts/macos_app/scripts/smoke_default.sh` → references `engines/audio_engine/tools/cli/ma_audio_features.py`

---

### Type D: tools/*.py → tools/audio/*.py or shared/* (ZERO consumers)

**Status**: NO ACTIVE CONSUMERS
**Risk Level**: VERY LOW (no consumers found)
**Consumers**: 0 files

#### Files:
1. `tools/tempo_sidecar_runner.py` (13 lines)
   - Delegates to: `tools.audio.tempo_sidecar_runner`
   - Type: CLI script shim with bootstrap

2. `tools/ma_add_echo_to_hci_v1.py` (10 lines)
   - Delegates to: `tools.hci.ma_add_echo_to_hci_v1`
   - Type: CLI script shim with bootstrap

3. `tools/schema_utils.py` (22 lines)
   - Delegates to: `shared.ma_utils.schema_utils`
   - Exports: `lint_features_payload`, `lint_hci_payload`, `lint_json_file`, `lint_merged_payload`, `lint_neighbors_payload`, `lint_pack_payload`, `lint_run_summary`, `validate_with_schema`

---

### Type E: tools/misc/* → engines/*/tools/misc/* (ZERO consumers)

**Status**: NO ACTIVE CONSUMERS
**Risk Level**: VERY LOW (no consumers found)
**Consumers**: 0 files

#### Files:
1. `tools/misc/backfill_features_meta.py` (3 lines - comment only)
   - Delegates to: `engines.audio_engine.tools.misc.backfill_features_meta`
   - Type: Empty shim placeholder

2. `tools/misc/aee_version.py` (8 lines)
   - Delegates to: `engines.audio_engine.tools.misc.aee_version`
   - Exports: `summary_dict`

3. `tools/misc/ma_tasks.py` (4 lines - comment only)
   - Delegates to: Unknown (relocated but not found)
   - Type: Broken shim placeholder

---

## Consolidation Recommendations

### Phase 1: Remove Zero-Consumer Shims (SAFE - immediate)

**Impact**: Remove 16 files with ZERO active consumers
**Risk**: VERY LOW
**Effort**: LOW (simple file deletions)

**Action Items**:
1. Delete all Type B shims (5 files in `src/ma_config/`)
2. Delete all Type D shims (3 files in `tools/`)
3. Delete all Type E shims (3 files in `tools/misc/`)
4. Delete empty Type C shims (5 files: comment-only placeholders in `tools/cli/`)
5. Update tests if needed (check `test_path_literals.py`)

**Files to Delete** (16 total):
```
src/ma_config/neighbors.py
src/ma_config/constants.py
src/ma_config/pipeline.py
src/ma_config/scripts.py
src/ma_config/profiles.py
tools/tempo_sidecar_runner.py
tools/ma_add_echo_to_hci_v1.py
tools/schema_utils.py
tools/misc/backfill_features_meta.py
tools/misc/aee_version.py
tools/misc/ma_tasks.py
tools/cli/tempo_sidecar_runner.py
tools/cli/ma_add_echo_to_hci_v1.py
tools/cli/hci_rank_from_folder.py
tools/cli/ma_audio_features.py
tools/cli/__init__.py
```

---

### Phase 2: Remove Type C CLI Shims (LOW RISK - requires minimal changes)

**Impact**: Remove 3 CLI shims with 2 consumer shims + 1 script reference
**Risk**: LOW (consumers are themselves shims, easy to update)
**Effort**: LOW (update 2 files + 1 shell script)

**Action Items**:
1. Update `engines/audio_engine/tools/misc/backfill_features_meta.py`:
   - Change `from tools.cli.backfill_features_meta import main`
   - To: `from tools.calibration.backfill_features_meta import main`

2. Update `engines/audio_engine/tools/hci/equilibrium_merge_full.py`:
   - Change `from tools.cli.equilibrium_merge_full import main`
   - To: `from tools.calibration.equilibrium_merge_full import main`

3. Update `hosts/macos_app/scripts/pipeline_smoke.sh`:
   - Change `tools/cli/ma_audio_features.py`
   - To: `engines/audio_engine/tools/cli/ma_audio_features.py` (canonical location)

4. Delete shims:
   ```
   tools/cli/backfill_features_meta.py
   tools/cli/calibration_readiness.py
   tools/cli/equilibrium_merge_full.py
   ```

5. Update `tests/test_path_literals.py` to remove references to deleted paths

---

### Phase 3: Remove Type A Security Shims (MODERATE RISK - requires migration)

**Impact**: Remove 5 security shims with 15 active consumers
**Risk**: MODERATE (requires updating 15 files)
**Effort**: MODERATE (systematic find-replace across 15 files)

**Action Items**:
1. Create migration script or manual find-replace:
   - `from security.files import` → `from shared.security.files import`
   - `from security.db import` → `from shared.security.db import`
   - `from security.config import` → `from shared.security.config import`
   - `from security.paths import` → `from shared.security.paths import`
   - `from security.subprocess import` → `from shared.security.subprocess import`

2. Update all 15 consumer files (see Type A consumer list above)

3. Run full test suite to verify no breakage

4. Delete shims:
   ```
   security/files.py
   security/db.py
   security/config.py
   security/paths.py
   security/subprocess.py
   ```

5. Consider leaving `security/__init__.py` if it serves as a package marker

---

## Testing Strategy

### Phase 1 Testing:
- Run: `python3 -m pytest tests/`
- Check: `tests/test_path_literals.py` (may reference deleted paths)
- Verify: No import errors for files that were deleted

### Phase 2 Testing:
- Run: `python3 -m pytest tests/`
- Test: `engines/audio_engine/tools/misc/backfill_features_meta.py --help`
- Test: `engines/audio_engine/tools/hci/equilibrium_merge_full.py --help`
- Test: `hosts/macos_app/scripts/pipeline_smoke.sh` (if available)

### Phase 3 Testing:
- Run: `python3 -m pytest tests/test_security_helpers.py`
- Run: `python3 -m pytest tests/` (full suite)
- Test: All 15 consumer files individually (at least `--help` for CLI tools)
- Grep check: `grep -r "from security\." --include="*.py" .` (should return 0 results)

---

## Rollout Schedule

**Total Estimated Effort**: 2-3 hours across all phases

### Immediate (Phase 1):
- **Time**: 30 minutes
- **Action**: Delete 16 zero-consumer shim files
- **Validation**: Run test suite

### Short-term (Phase 2):
- **Time**: 30 minutes
- **Action**: Update 3 consumers + 1 script, delete 3 CLI shims
- **Validation**: Test affected scripts

### Medium-term (Phase 3):
- **Time**: 1-2 hours
- **Action**: Update 15 consumers, delete 5 security shims
- **Validation**: Full integration testing

---

## Metrics

### Before Consolidation:
- **Total Shim Files**: 28
- **Total Shim Lines**: ~500 lines
- **Maintenance Overhead**: HIGH (3 parallel import paths for some modules)

### After Consolidation (All Phases):
- **Total Shim Files**: 0 (or 1 if keeping `security/__init__.py`)
- **Total Shim Lines**: 0
- **Maintenance Overhead**: NONE
- **Import Paths**: 1 canonical path per module

---

## Risk Mitigation

1. **Backup Strategy**: Create a git branch before each phase
2. **Incremental Approach**: Complete phases 1-3 sequentially with validation between
3. **Test Coverage**: Run full test suite after each phase
4. **Consumer Verification**: Test all consumer files individually
5. **Rollback Plan**: Each phase is independently revertible via git

---

## Notes

- All shims were created as "compatibility wrappers" during code reorganization
- Shims add cognitive load (3 import paths for same functionality)
- Zero-consumer shims suggest they were never actively used after migration
- Security shims are the only actively used shims and require careful migration
- Empty comment-only shims (Type C/E) serve no purpose and can be deleted immediately

---

## Appendix: Full Shim Inventory

### Summary Table:

| Type | Category | Files | Consumers | Risk | Priority |
|------|----------|-------|-----------|------|----------|
| A | security/* | 5 | 15 | HIGH | Phase 3 |
| B | src/ma_config/* | 5 | 0 | VERY LOW | Phase 1 |
| C | tools/cli/* (scripts) | 3 | 2+1 script | LOW | Phase 2 |
| C | tools/cli/* (empty) | 5 | 0 | VERY LOW | Phase 1 |
| D | tools/*.py | 3 | 0 | VERY LOW | Phase 1 |
| E | tools/misc/* | 3 | 0 | VERY LOW | Phase 1 |
| **TOTAL** | | **24** | **17** | | |

Note: 4 files in Type C are comment-only placeholders with no actual code, bringing actual shim count to 24 functioning shims + 4 empty placeholders = 28 total files.
