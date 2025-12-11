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

Chat smoke (quick verification)

```bash
cd hosts/macos_app
./scripts/chat_smoke.sh             # builds mac app + runs chat_engine/cli_smoke.py
# optional prompt override:
./scripts/chat_smoke.sh --prompt "Hello"
# optional context override:
./scripts/chat_smoke.sh --prompt "Hello" --context "/path/to/your.client.rich.txt"
```

Pipeline smoke (Python CLI)

```bash
cd hosts/macos_app
./scripts/pipeline_smoke.sh /path/to/audio.wav /tmp/ma_features_smoke.json
```

Manual quick checks (UI)

- Run the app: `./scripts/swift_run_local.sh`
- In Console tab: pick a context (history or last-run), send a prompt, confirm badges update and toast slide/fade.
- Run tab: drop an audio file, run, and reveal/preview sidecar; chat context should use the last run when present.
- Full checklist: see `docs/ui_smoke.md` for a step-by-step smoke.

CI notes

- Sparse smokes synthesize a 0.5s 440 Hz tone (tests/fixtures/audio/tone_440.wav) and run `ma_audio_features.py` against it.

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
- Busy views (Run/History) default to calmer cards (lens/glass opt-in per card), backdrop uses a cool subtle gradient + light noise; buttons have softened hover/focus sheen.
- Focus/keyboard: softened focus rings on primary Run controls and History search; History search has a clear “x”; Run shortcuts stay as before (⌘⏎, ⇧⌘⏎, ⌥⌘⏎, ⌘R, ⌘T, ⌘F, ⌘L).
- Persistence: Application Support is created before SQLite init so saved tracks load on first launch without tab toggles; sidecar actions are gated (friendly “No sidecar yet” until present).
- Shortcuts: ⌘⏎ run, ⇧⌘⏎ defaults, ⌥⌘⏎ smoke, ⌘R reveal last sidecar, ⌘T theme, ⌘F history search, ⌘L console prompt.
- Accessibility labels on key controls; missing-file guards for reveal/re-run; stronger glass depth on core panels and cards.
- MAStyle-backed components everywhere: `AlertBanner`, `PromptBar`, `HeaderBar`/`CardHeader`, `ChipRow` + `FABPopover` (snippets palette), `RailToggleOverlay`. Rail width tuned (≈72.6) so “History/Chat” fit without clipping; rail toggle hugs the border and stays subtle. Toasts auto-dismiss (default from `MAStyle.ToastDefaults.autoDismissSeconds`) with a left-slide/accordion fade and progress bar; close button uses the same exit.

Intended architecture

- UI: SwiftUI.
- Engines: Python remains the brain (Historical Echo, HCI, TTC, Lyric). Add IPC/CLI when ready.
- Audio: AVAudioEngine or future JUCE plug-in for DAW probes; keep real-time work off the UI thread.
- Chat: a new `engines/chat_engine/` scaffold wraps the existing `tools/chat` backend; future work moves chat logic/context/rate handling into that engine for all hosts.

Next integration steps

- Wire CLI/IPC to Python engines for real runs.
- Stream live logs into Console, true “re-run” using history metadata.
- Add signed/notarized packaging when needed.

CLI runner env overrides

- `MA_APP_CMD="/usr/bin/python3"` (default cmd)
- `MA_APP_ARGS="tools/cli/ma_audio_features.py --audio tone.wav --out /tmp/out.json"` (default args)
- `MA_APP_WORKDIR="/Users/you/music-advisor"`
- `MA_APP_ENV_FOO=bar` (extra env; prefix keys with `MA_APP_ENV_`)
