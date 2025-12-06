# Music Advisor macOS host (Swift/SwiftUI, no JUCE)

Purpose
- Provide a minimal macOS shell you can grow into the production host.
- Keep concerns separated: SwiftUI UI + IPC/CLI to Python engines; JUCE optional later (for audio UI or shared DSP).

What’s included
- SwiftPM app at `hosts/macos_app/` targeting macOS 12+, Swift 5.7+.
- SwiftUI shell with a configurable CLI runner (call your Python pipeline or a mock). No external deps.

Build/run (CLI)
```bash
cd hosts/macos_app
swift build
swift run
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
```

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

UI behavior
- “Run defaults” refills fields from env/defaults and executes.
- Results use a segmented view (JSON/stdout/stderr) with parsed JSON prettified when possible.
- Each run logs to `/tmp/macos_app_cmd.log` for quick debugging.

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
