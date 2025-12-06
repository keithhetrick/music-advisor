# macOS host scaffold (Swift/SwiftUI, no JUCE)

Why this exists
- A lightweight native shell to host Music Advisor UI and call the Python engines via IPC/CLI later.
- Keeps JUCE optional: plug-ins/DSP can arrive later without entangling the host UI.

Location
- `hosts/macos_app/` (SwiftPM package, macOS 12+, Swift 5.9).

How to run
```bash
cd hosts/macos_app
swift build
swift run
# or open Package.swift in Xcode
```

What it does today
- Shows a minimal SwiftUI window stating it’s the macOS host shell.
- No external deps; good for proving the Swift toolchain is ready.

Intended architecture
- UI: SwiftUI.
- Engines: Python remains the brain (Historical Echo, HCI, TTC, Lyric). Add IPC/CLI when needed.
- Audio: AVAudioEngine or future JUCE plug-in for DAW probes; keep real-time DSP off the UI thread.

Next integration steps
- Add IPC/CLI hooks to the Python pipeline (local-only).
- Render real feature outputs/sidecars in the UI.
- Add local logging/telemetry if needed (no network).***
