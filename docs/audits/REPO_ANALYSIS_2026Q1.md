# Music Advisor Repository Analysis

## Executive Summary

**Music Advisor** is a local-first audio analysis tool for comparing songs against historical hit data. It extracts audio features (tempo, key, loudness, energy, etc.), compares them to a corpus of hit songs, and provides actionable feedback—all without sending audio to external services.

The codebase is ~78,000 lines of Python across ~890 files, plus Swift (macOS app), C++ (JUCE plugins), and shell scripts. It's architected as a monorepo with distinct engines, hosts, shared libraries, and tools.

---

## Architecture Overview

```
music-advisor/
├── engines/           # Core processing engines
│   ├── audio_engine/     # Feature extraction (ma_audio_engine)
│   ├── lyrics_engine/    # Lyric/STT processing
│   ├── ttc_engine/       # Time-to-chorus estimation
│   └── recommendation_engine/  # Advisory logic
├── hosts/             # User-facing applications
│   ├── advisor_host/     # CLI/chat interface
│   ├── advisor_host_core/  # Shared host contracts
│   └── macos_app/        # SwiftUI desktop app
├── shared/            # Cross-cutting concerns
│   ├── config/           # Path resolution, env handling
│   ├── calibration/      # ML model calibration data
│   ├── security/         # Subprocess/file security
│   └── ma_utils/         # Shared utilities
├── tools/             # CLI tools, sidecars, scripts
├── infra/             # Build/deployment scripts
└── tests/             # Integration tests
```

### Data Flow

```
Audio File → ma_audio_features.py → features.json
                     ↓
              (optional sidecar: Essentia/Madmom)
                     ↓
           equilibrium_merge.py → merged.json
                     ↓
              pack_writer.py → client.json + *.pack.json
                     ↓
        HCI scoring/echo injection → hci.json + client.rich.txt
```

---

## Strengths

### 1. Privacy-First Design

- Audio never leaves the machine—only extracted features are processed
- Fully offline after initial data bootstrap
- Clear separation between local processing and external data sources

### 2. Defensive Error Handling

- Sidecar fallback chain (Essentia → Madmom → librosa)
- Timeout/retry logic with configurable limits
- QA gates for clipping, silence, low-level detection

### 3. Comprehensive Logging & Observability

- Structured JSON logging option (`LOG_JSON=1`)
- Stage timing instrumentation
- Redaction support for sensitive paths (`LOG_REDACT=1`)

### 4. Schema Validation

- JSON schemas for pack, neighbors, features outputs
- Lint functions for payload validation
- Schema-first contracts for downstream consumers

### 5. Flexible Configuration

- Extensive env var overrides (`MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`, etc.)
- Backend registry for enabling/disabling tempo backends
- QA policy presets (strict/lenient/default)

---

## Weaknesses & Pain Points

### 1. **Monolithic Feature Extractor** (Critical)

`tools/audio/ma_audio_features.py` is **1,747 lines** handling:

- Audio loading/normalization
- Tempo estimation (librosa + external sidecar)
- Key/mode estimation
- Energy/danceability/valence calculation
- QA metrics
- Caching
- CLI argument parsing
- Sidecar orchestration

**Impact**: Hard to test in isolation, difficult to modify one concern without touching others, cognitive overload for maintainers.

**Recommendation**: Extract into modules:

- `audio_loader.py` - load/normalize audio
- `tempo_estimator.py` - tempo estimation logic
- `feature_calculator.py` - energy/dance/valence
- `qa_checker.py` - quality assurance
- `cache_manager.py` - feature caching

### 2. **Excessive Shim/Wrapper Layer** (High)

The codebase has ~50+ files that are just shims:

```python
# tools/ma_audio_features.py (shim)
from tools.audio.ma_audio_features import main
if __name__ == "__main__":
    raise SystemExit(main())

# security/config.py (shim)
from shared.security.config import *  # noqa: F401,F403

# src/ma_config/paths.py (shim)
from shared.config.paths import *  # noqa: F401,F403
```

**Impact**:

- Import confusion—which file is the "real" one?
- 351 `# noqa` suppressions to hide star import warnings
- Maintenance burden keeping shims in sync

**Recommendation**:

- Consolidate to single source locations
- Use `__init__.py` re-exports instead of file-level shims
- Consider Python namespace packages

### 3. **Star Import Anti-Pattern** (High)

50+ files using `from X import *`:

```python
from shared.security.config import *  # noqa: F401,F403
```

**Impact**:

- Namespace pollution
- Unclear what's actually imported
- Breaks static analysis tools
- Makes refactoring dangerous

**Recommendation**: Explicit imports:

```python
from shared.security.config import CONFIG, SecurityConfig
```

### 4. **Global State & Mutable Loggers** (Medium)

Multiple files use `global` for logger reconfiguration:

```python
# tools/audio/ma_audio_features.py:1606
global LOG_JSON, LOG_REDACT, LOG_REDACT_VALUES, _log
```

**Impact**:

- Thread-unsafe if any parallelization is added
- Makes testing difficult (logger state bleeds between tests)
- Hidden dependencies between functions

**Recommendation**:

- Pass loggers explicitly or use dependency injection
- Use `logging.getLogger(__name__)` pattern
- Consider context variables for request-scoped logging

### 5. **Broad Exception Handling** (Medium)

654 instances of `except Exception:` catches:

```python
try:
    # some operation
except Exception:
    pass  # or return default
```

**Impact**:

- Swallows important errors (KeyboardInterrupt, SystemExit sometimes)
- Makes debugging difficult
- Can mask bugs that should fail loudly

**Recommendation**:

- Catch specific exceptions
- Log swallowed exceptions at DEBUG level
- Use `except Exception as e:` and log `e`

### 6. **Duplicated Pipeline Orchestration** (Medium)

Pipeline steps are orchestrated in multiple places:

- `automator.sh` (450 lines of bash)
- `smoke_full_chain.sh` (380 lines of zsh)
- `pipeline_driver.py`
- `pipeline_runner.py`

Each has slightly different:

- Environment setup
- Error handling
- Stage ordering
- Output paths

**Impact**:

- Fixes applied to one may not reach others
- Inconsistent behavior between invocation methods
- Hard to reason about "canonical" execution path

**Recommendation**:

- Single Python orchestrator with shell wrapper
- Shell scripts call Python driver, don't duplicate logic
- Configuration-driven stage selection

### 7. **Inconsistent Naming Conventions** (Low)

Mixed naming across files:

- `ma_audio_features.py` vs `equilibrium_merge.py` vs `pack_writer.py`
- `hci_final_score.py` vs `ma_simple_hci_from_features.py`
- `smoke.features.json` vs `*.features.json` vs `features.json`

**Recommendation**: Establish and document naming conventions.

### 8. **Test Coverage Gaps** (Medium)

- Most test files are small (< 100 lines)
- The 1,747-line `ma_audio_features.py` has minimal direct test coverage
- Integration tests exist but unit tests for core logic are sparse

**Recommendation**:

- Add unit tests for extracted modules
- Property-based testing for numerical functions
- Snapshot tests for JSON output schemas

---

## Redundancies

### 1. Duplicate Tool Definitions

Several tools exist in multiple locations:

- `tools/ma_audio_features.py` (shim) → `tools/audio/ma_audio_features.py` (real)
- `tools/cli/ma_audio_features.py` (shim) → engine CLI
- Multiple `equilibrium_merge.py` variants

### 2. Path Resolution

Path helpers are defined in:

- `shared/config/paths.py` (source of truth)
- `src/ma_config/paths.py` (shim)
- `security/config.py` → `shared/security/config.py` (shim chain)

### 3. Logging Setup

Logger creation repeated in many files with slight variations:

```python
LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
_log = make_logger(...)
```

Should be centralized factory.

### 4. Schema Validation

Validation functions in:

- `shared/ma_utils/schema_utils.py`
- `ma_audio_engine/schemas.py`
- Individual tools with inline validation

---

## Bottlenecks

### 1. Sidecar Execution (Performance)

External sidecar (Essentia/Madmom) is the slowest part:

- 90-second default timeout
- Single-threaded execution
- No warm-up or connection pooling

**Recommendation**:

- Batch mode for multiple files
- Optional daemon mode for sidecars
- Cache sidecar results more aggressively

### 2. Audio Loading (Memory)

Full audio loaded to memory:

```python
y, sr = load_audio_mono(path)  # entire file in RAM
```

For long files (> 10 minutes), this can consume significant memory.

**Recommendation**: Streaming/chunked processing for very long files.

### 3. Sequential Stage Execution

Pipeline stages run sequentially even when independent:

```
features → merge → pack → hci_score → philosophy → echo
```

Some stages could run in parallel (e.g., philosophy_hci and tempo_norms).

---

## Potential Leaks

### 1. Temp File Cleanup

Sidecar adapter creates temp files:

```python
tempdir = tempfile.TemporaryDirectory(prefix="ma_sidecar_")
# ... on error path, tempdir.cleanup() may not be called
```

While mostly handled, error paths could leak temp files.

### 2. File Handle Management

Some places use `open()` without context managers:

```python
with open(path, "r") as f:
    return json.load(f)
```

Most are correct, but a few spots could leak handles on exception.

### 3. Cache Growth

Sidecar cache in `.ma_cache/sidecar/` has a cap but:

- `SIDECAR_CACHE_MAX_BYTES` enforcement is best-effort
- Feature cache can grow unbounded if not GC'd

---

## Logic Issues

### 1. Race Condition in Cache Write

```python
# ma_audio_features.py
if sidecar_cache_path and not sidecar_cache_path.exists():
    atomic_write_json(sidecar_cache_path, sidecar_data)
```

TOCTOU race: file could be created between check and write.

### 2. Inconsistent Backend Detection

```python
is_defaultish = "tempo_sidecar_runner.py" in cmd_template
```

String matching for backend detection is fragile.

### 3. Fallback Logic Complexity

The sidecar fallback chain has complex state:

- `sidecar_status` can be: not_requested, requested, used, invalid, timeout, failed, cache_hit, disabled
- Multiple variables track attempts, warnings, backend hints

This complexity makes it hard to reason about all possible states.

---

## Recommendations Summary

| Priority | Issue                    | Recommendation                |
| -------- | ------------------------ | ----------------------------- |
| Critical | Monolithic extractor     | Break into focused modules    |
| High     | Star imports             | Explicit imports everywhere   |
| High     | Shim proliferation       | Consolidate to single sources |
| Medium   | Global state             | Dependency injection          |
| Medium   | Broad exceptions         | Specific exception handling   |
| Medium   | Duplicated orchestration | Single Python driver          |
| Low      | Naming inconsistency     | Document conventions          |

---

## Quick Wins

1. **Replace star imports** with explicit imports (1-2 days)
2. **Add `__all__` to modules** to control exports (half day)
3. **Centralize logger factory** to reduce boilerplate (1 day)
4. **Add type hints** to core functions (ongoing)
5. **Extract QA checker** from ma_audio_features.py (1 day)

---

## Conclusion

Music Advisor has solid foundations—privacy-first design, defensive error handling, and comprehensive schema validation. The main technical debt is structural: a monolithic extractor, excessive shims, and duplicated orchestration logic. Addressing these would significantly improve maintainability and testability without requiring architectural changes to the core pipeline.

---

## Audit Progress (Updated: 2026-01-07)

### Overview

Following the recommendations in this audit, significant progress has been made on addressing technical debt, particularly around the monolithic feature extractor and duplicated logging patterns.

### Completed Tasks

#### Tasks 1-4: Star Import Elimination
- **Scope**: Eliminated star imports (`from x import *`) across the codebase
- **Files Modified**: 198 files
- **Impact**: Improved code clarity, reduced namespace pollution, better IDE support

#### Tasks 5-7, 10: Logger Factory Migration
- **Scope**: Migrated tools to centralized logger factory
- **Files Modified**: 14 tools (8 in Task 7, 1 in Task 10, others in Tasks 5-6)
- **Lines Removed**: ~150 lines of duplicated LOG_* environment variable parsing
- **Impact**: Centralized logging configuration, reduced boilerplate, consistent behavior

#### Task 8: QA Checker Extraction
- **Module Created**: `tools/audio/qa_checker.py` (196 lines)
- **Tests Created**: `tests/test_qa_checker.py` (269 lines, 17 tests)
- **Functions Extracted**:
  - `compute_qa_metrics()`: Clipping, silence, low-level detection
  - `determine_qa_status()`: Overall QA gate logic
  - `validate_qa_strict()`: Strict mode validation
- **Impact**: Isolated QA logic for reuse and testing

#### Task 9: Audio Loader Extraction
- **Module Created**: `tools/audio/audio_loader.py` (175 lines)
- **Tests Created**: `tests/test_audio_loader.py` (240 lines, 14 tests)
- **Functions Extracted**:
  - `load_audio()`: Wrapper for mono audio loading
  - `probe_audio_duration()`: Fast duration check via soundfile/ffprobe
- **Impact**: Consolidated audio I/O logic, reduced duplication

#### Task 11: Tempo Estimator Extraction
- **Module Created**: `tools/audio/tempo_estimator.py` (338 lines)
- **Tests Created**: `tests/test_tempo_estimator.py` (271 lines, 23 tests)
- **Functions Extracted**:
  - `robust_tempo()`: Beat tracking with librosa
  - `estimate_tempo_with_folding()`: Tempo estimation with folding logic
  - `select_tempo_with_folding()`: Select best tempo variant
  - `compute_tempo_confidence()`: Confidence scoring
- **Impact**: Isolated tempo logic, comprehensive test coverage

#### Task 12: Feature Calculator Extraction
- **Module Created**: `tools/audio/feature_calculator.py` (309 lines)
- **Tests Created**: `tests/test_feature_calculator.py` (351 lines, 28 tests)
- **Functions Extracted**:
  - `estimate_energy()`: Perceptual energy from RMS + spectral centroid
  - `estimate_danceability()`: Rhythm suitability from tempo + beat strength
  - `estimate_valence()`: Musical positivity from mode + energy
- **Impact**: Isolated feature calculations for reuse across tools

#### Task 13: Key Detector Extraction
- **Module Created**: `tools/audio/key_detector.py` (173 lines)
- **Tests Created**: `tests/test_key_detector.py` (274 lines, 25 tests)
- **Functions Extracted**:
  - `estimate_mode_and_key()`: Chroma-based key/mode detection
  - `key_confidence_label()`: Simple confidence heuristic
  - `normalize_key_confidence()`: Clamp confidence to 0.0-1.0
  - `NOTE_NAMES_SHARP`: Pitch class constant
- **Impact**: Isolated key detection logic, improved testability

### ma_audio_features.py Status

| Metric | Original | Current | Change |
|--------|----------|---------|--------|
| **Total Lines** | 1,747 | 1,391 | -356 lines (-20%) |
| **analyze_pipeline()** | ~650 lines | ~587 lines | -63 lines (-10%) |
| **main()** | ~250 lines | ~235 lines | -15 lines (-6%) |

#### Lines Extracted by Module

| Module | Lines | Tests | Test Lines | Coverage |
|--------|-------|-------|------------|----------|
| qa_checker.py | 196 | 17 tests | 269 | Comprehensive |
| audio_loader.py | 175 | 14 tests | 240 | Comprehensive |
| tempo_estimator.py | 338 | 23 tests | 271 | Comprehensive |
| feature_calculator.py | 309 | 28 tests | 351 | Comprehensive |
| key_detector.py | 173 | 25 tests | 274 | Comprehensive |
| **Total** | **1,191** | **107 tests** | **1,405** | **All modules** |

### Remaining Structure in ma_audio_features.py

The current file (1,391 lines) now primarily contains:

#### 1. Configuration & Constants (Lines 1-350, ~350 lines)
- Imports and path setup
- Constants (TARGET_SR, TARGET_LUFS, thresholds)
- Default configurations
- Tempo confidence defaults
- SciPy shim for librosa compatibility
- **Extraction Potential**: Low (configuration should remain centralized)

#### 2. Helper Functions (Lines 350-570, ~220 lines)
- `_sanitize_tempo_backend_fields()`: Backend validation
- `_ensure_feature_pipeline_meta()`: Metadata injection
- `_validate_external_payload()`: External data validation
- `build_config_fingerprint()`: Configuration hashing
- `debug()`: Logging helper
- `_pad_short_signal()`: Signal padding (still used internally)
- `compute_file_hash()`: File hashing
- `estimate_lufs()`: Loudness estimation (~20 lines)
- `normalize_audio()`: Audio normalization (~15 lines)
- `normalize_external_confidence()`: Confidence normalization (~30 lines)
- **Extraction Potential**: Medium
  - LUFS estimation could be extracted
  - Audio normalization could join audio_loader
  - External confidence normalization is tempo-specific (could stay or join adapters)

#### 3. Pipeline Core (Lines 570-1156, ~587 lines)
- `analyze_pipeline()`: Main feature extraction pipeline
  - Caching logic (~80 lines)
  - Sidecar orchestration (~120 lines)
  - External data merging (~100 lines)
  - Feature extraction coordination (~100 lines)
  - Output assembly (~100 lines)
  - Error handling (~87 lines)
- **Extraction Potential**: Medium-High
  - Caching could be extracted to `cache_orchestrator.py`
  - Sidecar logic could be extracted to `sidecar_orchestrator.py`
  - However, these are tightly coupled to the pipeline flow

#### 4. CLI Entry Point (Lines 1157-1391, ~235 lines)
- `main()`: Argument parsing and pipeline invocation
  - Argument parser setup (~80 lines)
  - Environment/settings loading (~30 lines)
  - Pipeline invocation (~20 lines)
  - Output writing (~30 lines)
  - Error handling (~75 lines)
- **Extraction Potential**: Low (CLI logic should remain with entry point)

### Remaining Extraction Candidates

#### High Value, Low Risk
- [ ] **LUFS Estimation** (~20 lines)
  - Extract `estimate_lufs()` to `tools/audio/loudness_estimator.py`
  - Clean separation from other features
  - Would add ~1 test file

#### Medium Value, Medium Risk
- [ ] **Audio Normalization** (~15 lines)
  - Extract `normalize_audio()` to join `audio_loader.py`
  - Logical fit with audio I/O operations
  - Requires careful dependency analysis

- [ ] **Caching Orchestration** (~80 lines)
  - Extract caching logic to `tools/audio/cache_orchestrator.py`
  - Currently embedded in `analyze_pipeline()`
  - Would require refactoring pipeline flow

- [ ] **Sidecar Orchestration** (~120 lines)
  - Extract to `tools/audio/sidecar_orchestrator.py`
  - Complex state management (8 status states)
  - Tightly coupled to pipeline, high refactoring cost

#### Low Value (Keep as-is)
- Configuration constants (should remain centralized)
- CLI argument parsing (belongs with entry point)
- Pipeline coordination logic (core responsibility of the file)

### Test Coverage Added

- **Total New Test Files**: 5
- **Total New Tests**: 107 tests
- **Total Test Lines**: 1,405 lines
- **Test-to-Code Ratio**: 1.18:1 (1,405 test lines / 1,191 extracted code lines)

All extracted modules have comprehensive test coverage including:
- Normal operation tests
- Edge case handling (None, empty, invalid inputs)
- Value range validation
- Integration/workflow tests
- Consistency/determinism tests

### Impact Summary

#### Code Quality Improvements
- **Modularity**: Broken down monolithic extractor into 5 focused modules
- **Testability**: Added 107 tests covering previously untested code
- **Maintainability**: Reduced cognitive load—each module has single responsibility
- **Reusability**: Extracted modules can be used by other tools

#### Quantitative Metrics
- **Lines Removed from ma_audio_features.py**: 356 lines (-20%)
- **New Module Lines**: 1,191 lines (across 5 modules)
- **Test Lines Added**: 1,405 lines
- **Net Addition**: +2,240 lines (includes comprehensive tests and documentation)

#### Future Work
The remaining `analyze_pipeline()` function (587 lines) is still complex but now primarily focused on its core responsibility: orchestrating the feature extraction pipeline. Further extractions (caching, sidecar) are possible but have diminishing returns vs. refactoring cost.

### Next Steps

1. **Consider LUFS extraction** (highest value, lowest risk)
2. **Evaluate audio normalization extraction** (clean fit with audio_loader)
3. **Monitor ma_audio_features.py complexity** as new features are added
4. **Continue test coverage expansion** for remaining helper functions

---

*Progress tracking ends. See commit history for detailed implementation.*
