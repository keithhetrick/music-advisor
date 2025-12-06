# Music Advisor macOS host (Swift/SwiftUI, no JUCE)

Purpose
- Provide a minimal macOS shell you can grow into the production host.
- Keep concerns separated: SwiftUI UI + IPC/CLI to Python engines; JUCE optional later (for audio UI or shared DSP).

What’s included
- SwiftPM app at `hosts/macos_app/` targeting macOS 12+, Swift 5.9.
- Simple SwiftUI window; no external deps.

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

Design/architecture notes
- UI: SwiftUI for native macOS host.
- Engines: Python remains the brain (Historical Echo, HCI, TTC, Lyric). Add IPC/CLI bindings later.
- Audio: Use AVAudioEngine or the future JUCE plug-in for in-DAW probes; keep real-time DSP out of the UI thread.

Next steps (when ready)
- Add IPC/CLI bridge to the Python pipeline (local calls; no network).
- Wire real feature outputs into the UI.
- Add minimal logging/telemetry (local-only).
