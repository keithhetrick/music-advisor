# macOS host (Swift/SwiftUI, no JUCE required)

Why this exists

- A lightweight native shell for Music Advisor that calls the Python engines via CLI/IPC (future).
- JUCE remains optional for DAW probes/DSP; the host UI is pure SwiftUI.

Location

- `hosts/macos_app/` (SwiftPM package, macOS 12+, Swift 5.7+).

How to run (fast local loop)

```bash
cd hosts/macos_app
./scripts/swift_run_local.sh
# builds and opens the .app (focus stays in the window)
# or manually:
# HOME=$PWD/build/home SWIFTPM_DISABLE_SANDBOX=1 swift build --scratch-path $PWD/build/.swiftpm --disable-sandbox
# HOME=$PWD/build/home SWIFTPM_DISABLE_SANDBOX=1 swift run   --scratch-path $PWD/build/.swiftpm --disable-sandbox
```

Package (unsigned dev zip)

```bash
cd hosts/macos_app
./scripts/package_release.sh
# outputs dist/MusicAdvisorMacApp.app and dist/MusicAdvisorMacApp.zip
```

What the UI is now

- Nav rail + adaptive split panes:
  - Run: drop zone + batch queue left; command/profile/run + results right.
  - History: filter/search left; preview card (reveal/preview/re-run) right.
  - Console: log + prompt, snippets that prefill/focus the prompt.
- Getting Started overlay, glassy MAStyle depth, non-blocking toasts, throttled alerts.
- Shortcuts: ⌘⏎ run, ⇧⌘⏎ defaults, ⌥⌘⏎ smoke, ⌘R reveal last sidecar, ⌘T theme, ⌘F history search, ⌘L console prompt.
- Accessibility labels on key controls; missing-file guards for reveal/re-run; stronger glass depth on core panels and cards.
- MAStyle-backed components everywhere: `AlertBanner`, `PromptBar`, `HeaderBar`/`CardHeader`, `ChipRow` + `FABPopover` (snippets palette), `RailToggleOverlay`. Rail width tuned (≈72.6) so “History/Chat” fit without clipping; rail toggle hugs the border and stays subtle.

Intended architecture

- UI: SwiftUI.
- Engines: Python remains the brain (Historical Echo, HCI, TTC, Lyric). Add IPC/CLI when ready.
- Audio: AVAudioEngine or future JUCE plug-in for DAW probes; keep real-time work off the UI thread.

Next integration steps

- Wire CLI/IPC to Python engines for real runs.
- Stream live logs into Console, true “re-run” using history metadata.
- Add signed/notarized packaging when needed.

CLI runner env overrides

- `MA_APP_CMD="/usr/bin/python3"` (default cmd)
- `MA_APP_ARGS="tools/cli/ma_audio_features.py --audio tone.wav --out /tmp/out.json"` (default args)
- `MA_APP_WORKDIR="/Users/you/music-advisor"`
- `MA_APP_ENV_FOO=bar` (extra env; prefix keys with `MA_APP_ENV_`)
