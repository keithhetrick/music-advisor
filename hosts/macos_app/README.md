# Music Advisor macOS host (Swift/SwiftUI)

Purpose

- Provide a minimal macOS shell you can grow into the production host.
- Keep concerns separated: SwiftUI UI + IPC/CLI to Python engines.

What’s included

- SwiftPM app at `hosts/macos_app/` targeting macOS 12+, Swift 5.7+.
- SwiftUI shell with a configurable CLI runner (call your Python pipeline or a mock). No external deps.

Build/run (CLI)

```bash
cd hosts/macos_app
swift build
swift run
```

Build/run with default HOME (no overrides)

```bash
cd hosts/macos_app
./scripts/swift_run_default.sh
```

Open in Xcode

```bash
cd hosts/macos_app
open Package.swift
```

Local build/run helper (uses local HOME + scratch path; tolerates locked global SwiftPM caches)

```bash
cd hosts/macos_app
./scripts/swift_run_local.sh
```

Package a release .app (unsigned zip for sharing)

```bash
cd hosts/macos_app
./scripts/package_release.sh
# outputs dist/MusicAdvisorMacApp.app and dist/MusicAdvisorMacApp.zip
```

Reset logs / clean builds

```bash
./scripts/clean_builds.sh       # wipe app build artifacts
./scripts/reset_run_log.sh      # remove last command log
```

Pin Python deps to expected ranges

```bash
./scripts/pin_python_deps.sh
```

Smoke test the default CLI (headless)

```bash
./scripts/smoke_default.sh
# or for CI hooks: ./scripts/run_smoke_ci.sh
# install a git pre-push hook to run smoke: ./scripts/install_prepush_hook.sh
```

UI tests (XCUI)

- Run `./scripts/ui_tests_with_coverage.sh` (or `task test-macos-ui`) to execute the `MusicAdvisorMacAppUITests` bundle with coverage enabled via the `MusicAdvisorMacApp-UI` scheme. Reports land in `build/ui-test-coverage.txt` and `build/ui-test-coverage.json`.
- Debug-only UI controls appear when `MA_UI_TEST_MODE=1` (set by the UI test target) so automation can seed the queue, enqueue a sample job, start the harness, and trigger a toast reliably.

Testing & coverage (macOS host)

- Full tests: `cd hosts/macos_app && swift test` (slow stop/restart queue cases now run by default).
- Optional stress/soak: `RUN_LARGE_QUEUE_STRESS=1 swift test --filter LargeQueueRobustnessTests` (add `RUN_SOAK=1` for longer budgets).
- Optional micro-benchmark: `RUN_QUEUE_BENCH=1 swift test --filter QueueEngineBenchmarks`.
- Temp-path lint (prod sources): `scripts/lint_tmp_paths.sh` (or `task lint-macos-tmp`).
- Coverage bundle: `./scripts/publish_coverage_artifacts.sh` (or `task publish-macos-coverage`) collects `coverage.txt`, UI coverage, and, if present, zips the latest `.xcresult` into `build/coverage-latest/`. If you need the xcresult, run UI tests first (`scripts/ui_tests_with_coverage.sh`).
- Taskfile convenience commands require go-task (`brew install go-task`), or run the scripts directly as shown.
- CI/local validation recommendations:
  - Per-PR: `swift test`, `scripts/ui_tests_with_coverage.sh` (or `task test-macos-ui`), `scripts/publish_coverage_artifacts.sh` to surface coverage.
  - Nightly/periodic: `task ci-macos-queue-all` (runs lint + fast + slow + stress + bench; add `RUN_SOAK=1` if desired), then `task publish-macos-coverage` to archive coverage/xcresult.
  - Enable a soft coverage threshold in CI using the generated `build/coverage-latest/` artifacts.
  - Hardened runtime / code signing: for release builds, turn on Hardened Runtime under Signing & Capabilities and use your team signing identity. (UI tests can remain with ad-hoc signing.)

Config overrides (no code edits)

- Optional `.env.local` (copy from `.env.local.example`) and/or JSON config at `config/defaults.json` (override path via `MA_APP_CONFIG_FILE`).
- Env has highest priority (`MA_APP_DEFAULT_*`, `MA_APP_ENV_*`, `MA_APP_CMD/ARGS/WORKDIR`), then JSON config, then code fallback.
- Profiles: define named presets in JSON (cmd/args/workdir/env/out). UI has a profile picker + “Apply profile” + “Reload config”.

Data storage (App Support, no hard-coded paths)

- All persisted app data (tracks/artists/queue/history/sidecars) lives under `~/Library/Application Support/MusicAdvisorMacApp` for the current user, following macOS conventions via `FileManager.default.urls(.applicationSupportDirectory, ...)`.
- Running with an overridden `HOME` (e.g., `HOME=$PWD/build/home … swift run`) will redirect to `"$HOME/Library/Application Support/MusicAdvisorMacApp"`. Ensure that directory exists or copy your DB there if you want to reuse data in a sandboxed run.
- No absolute paths are hard-coded; the active App Support path is entirely determined by the environment’s `HOME`.

Design/architecture notes

- UI: SwiftUI for native macOS host.
- Engines: Python remains the brain (Historical Echo, HCI, TTC, Lyric). Add IPC/CLI bindings later.
- Audio: Use AVAudioEngine or the future JUCE plug-in for in-DAW probes; keep real-time DSP out of the UI thread.
- CLI runner defaults are pre-filled for this repo/machine:
  - Command: `/usr/local/bin/python3 /Users/keithhetrick/music-advisor/engines/audio_engine/tools/cli/ma_audio_features.py --audio /Users/keithhetrick/Downloads/lola.mp3 --out /tmp/ma_features.json`
  - Working dir: `/Users/keithhetrick/music-advisor`
  - Extra env: (add `PYTHONPATH=/Users/keithhetrick/music-advisor` if needed)
  - Override via env (picked up at app launch):
    - `MA_APP_CMD="/usr/local/bin/python3"`
    - `MA_APP_ARGS="/Users/keithhetrick/music-advisor/engines/audio_engine/tools/cli/ma_audio_features.py --audio /Users/keithhetrick/Downloads/lola.mp3 --out /tmp/ma_features.json"`
    - `MA_APP_WORKDIR="/Users/keithhetrick/music-advisor"`
    - `MA_APP_ENV_PYTHONPATH="/Users/keithhetrick/music-advisor"`
    - Other env: `MA_APP_ENV_FOO=bar` (prefix with `MA_APP_ENV_`)

Default overrides for other machines (env)

- `MA_APP_DEFAULT_CMD` (e.g., `/usr/bin/python3`)
- `MA_APP_DEFAULT_SCRIPT` (e.g., `/path/to/cli.py`)
- `MA_APP_DEFAULT_AUDIO` (e.g., `/path/to/audio.wav`)
- `MA_APP_DEFAULT_OUT` (e.g., `/tmp/ma_features.json`)
- `MA_APP_DEFAULT_WORKDIR`
- `MA_APP_ENV_PYTHONPATH`
- Optional `.env.local` (copied from `.env.local.example`) can set these without shell exports. Override file path with `MA_APP_ENV_FILE`.

UI behavior

- “Run defaults” refills fields from env/defaults and executes.
- “Run smoke” calls `scripts/smoke_default.sh` headless to verify the default CLI and sidecar.
- Results use a segmented view (JSON/stdout/stderr) with parsed JSON prettified when possible.
- Each run logs to `/tmp/macos_app_cmd.log` for quick debugging.
- Inline helpers: copy JSON to clipboard; reveal sidecar in Finder; summary metrics (tempo/key/duration/LUFS/peak/crest); last run time + duration shown in the header.

Dependency note (Python CLI)

- If you see warnings about numpy/scipy/librosa versions, you can pin to the expected ranges in the same Python you run from the app:

  ```bash
  cd /Users/keithhetrick/music-advisor
  PYTHONPATH=$PWD /usr/local/bin/python3 -m pip install "numpy<2" "scipy<1.12" "librosa>=0.10,<0.11"
  ```

Next steps (when ready)

- Add IPC/CLI bridge to the Python pipeline (local calls; no network).
- Wire real feature outputs into the UI.
- Add minimal logging/telemetry (local-only).
