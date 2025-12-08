# MAStyle JUCE UI Demo

Minimal JUCE plugin that showcases custom vector UI controls (rotary dials, envelope preview, meter) and a simple DSP shell. Intended as a portfolio/demo that maps mockups to live controls while keeping the audio path safe and lightweight.

## What it demonstrates

- Custom rotary dials with arc/pointer styling and label.
- Envelope mini-view driven by attack/release parameters.
- Simple RMS meter updated from the processor.
- Real-time-safe DSP shell + probe sidecar: gain/drive, low-pass filter, dry/wet mix; collects RMS/peak/crest and writes a JSON sidecar in a background thread (no audio-thread allocations).
- Modern JUCE + CMake workflow, Xcode or CLI builds, AU/VST3/Standalone targets.

## Layout

```bash
plugins/juce_ui_demo/
  CMakeLists.txt
  Source/
    PluginProcessor.{h,cpp}   // DSP + parameters (APVTS)
    PluginEditor.{h,cpp}      // Custom UI controls (dials, envelope, meter)
```

## Build (CLI)

```bash
cd plugins/juce_ui_demo
# Point JUCE_DIR at your JUCE checkout (submodule or sibling). Default: ./JUCE
cmake -B build -G Xcode -DJUCE_DIR=/path/to/JUCE
cmake --build build --config Debug      # or Release
```

Artifacts:

- Standalone app: `build/Debug/MAStyle JUCE Demo.app`
- VST3: `build/Debug/MAStyle JUCE Demo.vst3`
- AU: `build/Debug/MAStyle JUCE Demo.component`

Sidecars:

- Writes to `~/music-advisor/data/features_output/juce_probe/<track>/<timestamp>/juce_probe_features.json` with RMS/peak/crest.

## Notes

- Deployment target: macOS 12+, C++17.
- No MIDI; stereo in/out.
- Audio thread is allocation-free; parameters are APVTS-backed.
- Use Xcode’s Audio Unit host or JUCE AudioPluginHost to load the plugin.
- Precompiled headers are disabled here to avoid ObjC/PCH conflicts; rebuilds remain clean under Ninja.

## Streamlined (presets + install)

```bash
cd plugins/juce_ui_demo
# Fast dev (Ninja, Standalone-only; adjust JUCE_DIR in CMakePresets.json if needed):
cmake --preset juce-ninja
cmake --build --preset juce-ninja-build
# Run Standalone:
open build-ninja/MAStyleJuceDemo_artefacts/Debug/Standalone/MAStyle\ JUCE\ Demo.app

# Install AU/VST3 to user root plugin folders (no vendor subfolder):
./scripts/install_root.sh Debug   # or Release

# One-liner to rebuild+install+register AU (Logic): 
# ./scripts/refresh_au.sh Debug

# If a host doesn’t see it and you don’t want to rescan everything:
# Targeted refresh (avoids wiping full AU cache):
# pluginkit -m -r ~/Library/Audio/Plug-Ins/Components/MAStyle\ JUCE\ Demo.component
# killall -9 AudioComponentRegistrar 2>/dev/null || true
# Then reopen the host and rescan only this plugin.
```

Xcode/packaging path (kept intact):

```bash
cmake --preset juce-xcode
cmake --build --preset juce-xcode-build
```

Notes:

- If Ninja complains about missing system headers, ensure Xcode is installed/selected and `CMAKE_OSX_SYSROOT` in `CMakePresets.json` points to your current SDK (`/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`).
- PCH is disabled to avoid ObjC++ conflicts in JUCE modules; no action needed—just rebuild.
- VS Code: tasks and launch are wired for the Ninja standalone loop:
  - Build: “CMake: Build (Ninja, Standalone)”
  - Launch: “Run MAStyle Standalone (Ninja)” (pre-builds, then runs the app from `build-ninja/…/Debug/Standalone`).
- Cross-host quick check (no Logic rescan): open the VST3 in JUCE AudioPluginHost/REAPER:
  `~/Library/Audio/Plug-Ins/VST3/MAStyle JUCE Demo.vst3`

## Packaging (example)

```bash
cmake --build build --config Release
cmake --install build --config Release --prefix dist
# Zip dist or copy the .vst3/.component to your user plugin folders for testing
# Skeleton signed packaging (manual signing/notarization):
./scripts/package_release_signed.sh
```

### Signing / Notarization (manual steps)
- Env vars (optional):
  - `DEV_ID_APP="Developer ID Application: Your Name (TEAMID)"`
  - `NOTARY_APPLE_ID`, `NOTARY_TEAM_ID`, `NOTARY_APP_SPECIFIC_PW`
- Run after a Release build: `./scripts/package_release_signed.sh`
  - Stages AU/VST3/app to `dist/`
  - Codesigns if `DEV_ID_APP` is set
  - Creates a zip
  - Notarizes + staples if `NOTARY_*` vars are set
- Distribute the stapled bundles/zip from `dist/`.

## UI/DSP demo notes
- Custom vector controls: halo knob, envelope mini-view, step sequencer, animated SVG badge.
- DSP shell: drive + tone + step modulation, dry/wet, RMS meter feeding sidecar writer (background thread).

## Portfolio alignment (JD highlights)
- Translate mockups → live vector graphics: bespoke halo knob, mini-envelope, step sequencer, animated SVG badge.
- Complex UI controls: multiple APVTS-bound custom controls with styling tokens (GuiStyle), modularized under `Source/gui/controls/`.
- UX/UI R&D loop: fast Ninja + Standalone for immediate feedback; VST3 usable in lightweight hosts for quick reloads.
- Packaging: CMake presets, install scripts, and signing/notarization checklist (`scripts/package_release_signed.sh`).
- Architecture/modularity: processor/editor split, small focused control files, APVTS-based state, ParameterID version hints for safe AU evolution.
- Cross-host readiness: AU/VST3/Standalone artifacts built; VST3 handy for non-Logic hosts when avoiding AU rescans.
