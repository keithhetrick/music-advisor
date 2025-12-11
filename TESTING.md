# Testing Guide

> Prereq: Taskfile commands require [go-task](https://taskfile.dev) (`brew install go-task` on macOS). You can always run the underlying scripts/commands directly if Task is unavailable.

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

## macOS app (SwiftUI host)

- Unit/UI tests: `cd hosts/macos_app && swift test`
- Coverage: `cd hosts/macos_app && scripts/test_with_coverage.sh` (writes `.build/coverage.txt`)
- UI (XCUI) with coverage: `cd hosts/macos_app && scripts/ui_tests_with_coverage.sh`
  - Coverage artifacts land in `hosts/macos_app/build/ui-test-coverage.txt` and `.json`.
  - Expect harmless Xcode attachment warnings during UI runs (screenshot writes can be sandboxed); results/coverage still emit.
  - CI: archive the latest xcresult (`build/ui-tests-derived/Logs/Test/*.xcresult` or zipped `build/ui-tests-latest.xcresult.zip`) and the coverage files above.
  - Current state: UI tests re-enabled; if flakiness is observed, use the manual checklist below to validate critical flows.
- Requires Xcode toolchain on macOS; coverage run may need permission to write to module caches.
- Queue stress shortcuts:
  - Fast deterministic sweep: `task test-macos-queue-fast` (runs LargeQueueRobustnessTests quick path).
  - Full stress/soak: `task test-macos-queue-stress` (sets `RUN_LARGE_QUEUE_STRESS=1`; add `RUN_SOAK=1` for longer budgets).
- Slow stop/restart queue tests now run by default (previously opt-in).
- Optional queue micro-benchmark: `RUN_QUEUE_BENCH=1 swift test --filter QueueEngineBenchmarks` or `task bench-macos-queue`.
- Lint for temp-path usage in prod sources: `task lint-macos-tmp`.
- Coverage publishing: `task publish-macos-coverage` collects unit/UI coverage and latest xcresult into `build/coverage-latest`.
- Coverage artifacts: after publishing, verify `hosts/macos_app/build/coverage-latest/coverage.txt`, `ui-test-coverage.txt`, and `ui-test-coverage.json` exist; CI uploads the same folder as an artifact.
- Full queue CI sweep: `task ci-macos-queue-all` (lint + fast + slow + stress + bench; add `RUN_SOAK=1` for longer stress budgets).
- CI guidance:
  - PR/CI: run `swift test`, `scripts/ui_tests_with_coverage.sh` (or `task test-macos-ui`), then `task publish-macos-coverage` to archive coverage/xcresult; enforce a soft coverage threshold using the artifacts in `build/coverage-latest/`.
  - Nightly: `task ci-macos-queue-all` to exercise lint, slow stop/restart, stress/soak (with `RUN_SOAK=1`), and the optional micro-benchmark.
  - Security: keep Hardened Runtime enabled for release builds in Xcode (Signing & Capabilities) and ad-hoc signing for UI tests; use `task lint-macos-tmp` in CI to prevent hard-coded temp paths in prod sources. Hardened Runtime is not forced in repo to avoid blocking unsigned local runs—enable it per-release.
  - Automated: `.github/workflows/macos-nightly.yml` runs unit/UI tests with coverage, lint, stress, and the opt-in micro-benchmark nightly and uploads `build/coverage-latest/`.
    - Optional coverage gate via `MACOS_MIN_COVERAGE` secret; the nightly workflow runs `scripts/check_coverage_threshold.sh`.
    - Opt-in stress/bench: set repo/org secrets `RUN_SOAK=1` and/or `RUN_QUEUE_BENCH=1` to execute long stress and micro-benchmarks in CI.

Manual macOS UI checklist (when skipping UITests):

- Launch with `MA_UI_TEST_MODE=1`.
- Run tab: Reset queue, verify running/pending/done/canceled rows; use debug buttons to Start/Stop, Make pending jobs canceled, Resume canceled (or Force resume canceled), Cancel pending, Clear canceled/failed/completed/all, and confirm queue card remains visible.
- Folder: Use “Expand folders” then expand “AlbumA” in the queue list and ensure it stays visible.
- Toast/settings: Tap “Show test toast” then “Open settings”; close via the X or “Close settings (UITest)”; ensure overlay disappears.
- Theme/history: Switch to History tab, toggle theme twice, return to Run.

Queue engine tests cover empty queue, stop/resume, failures, spawn errors, ingestion, history persistence, and large batch processing (see `hosts/macos_app/Tests/MusicAdvisorMacAppTests/*QueueEngine*.swift`, `HistoryPersistenceTests.swift`, and `LargeQueuePerformanceTests.swift`).
Large robustness sweeps (500/1000 jobs, mixed junk files) are opt-in via `RUN_LARGE_QUEUE_STRESS=1 swift test --filter LargeQueueRobustnessTests` to avoid long CI runs.

## MAStyle design system

- Unit tests: `cd shared/design_system && swift test`
- Coverage: `cd shared/design_system && scripts/test_with_coverage.sh` (writes `.build/coverage.txt`)
- These are standalone; no app launch required.

## Troubleshooting tests

- If path-related failures occur, ensure `MA_DATA_ROOT` is unset or points to a writable location.
- If dependencies are missing, reinstall with `pip install -r requirements.txt && pip install -r requirements.lock || true`.
