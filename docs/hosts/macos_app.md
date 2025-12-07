# macOS host scaffold (Swift/SwiftUI, no JUCE)

Why this exists
- A lightweight native shell to host Music Advisor UI and call the Python engines via IPC/CLI later.
- Keeps JUCE optional: plug-ins/DSP can arrive later without entangling the host UI.

Location
- `hosts/macos_app/` (SwiftPM package, macOS 12+, Swift 5.7+).

How to run
```bash
cd hosts/macos_app
swift build
swift run
# or open Package.swift in Xcode
```

Local helper (uses local HOME + scratch path)
```bash
cd hosts/macos_app
./scripts/swift_run_local.sh
# or manually:
# HOME=$PWD/build/home swift build --scratch-path $PWD/build/.swiftpm
# HOME=$PWD/build/home swift run   --scratch-path $PWD/build/.swiftpm
```

Package (unsigned dev zip)
```bash
cd hosts/macos_app
./scripts/package_release.sh
# outputs dist/MusicAdvisorMacApp.app and dist/MusicAdvisorMacApp.zip
```

What it does today
- Shows a SwiftUI window with a configurable CLI runner (defaults to echo a JSON string).
- No external deps; good for proving the Swift toolchain is ready.

Intended architecture
- UI: SwiftUI.
- Engines: Python remains the brain (Historical Echo, HCI, TTC, Lyric). Add IPC/CLI when needed.
- Audio: AVAudioEngine or future JUCE plug-in for DAW probes; keep real-time DSP off the UI thread.

Next integration steps
- Add IPC/CLI hooks to the Python pipeline (local-only).
- Render real feature outputs/sidecars in the UI.
- Add local logging/telemetry if needed (no network).

CLI runner env overrides
- `MA_APP_CMD="/usr/bin/python3"` (default cmd)
- `MA_APP_ARGS="tools/cli/ma_audio_features.py --audio tone.wav --out /tmp/out.json"` (default args)
- `MA_APP_WORKDIR="/Users/you/music-advisor"`
- `MA_APP_ENV_FOO=bar` (extra env; prefix keys with `MA_APP_ENV_`)***
