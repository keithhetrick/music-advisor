# JUCE UI Demo (MAStyle)

This is a lightweight JUCE plugin that showcases custom vector UI controls (rotary dials, envelope preview, meter) and a safe DSP shell. Use it as a portfolio-ready reference for translating mockups into live controls while following modern JUCE + CMake practices.

## Features

- Custom controls: rotary dials with arc/pointer styling, envelope mini-view (attack/release), simple RMS meter.
- Probe sidecar: collects RMS/peak/crest on the audio thread, writes `juce_probe_features.json` on a background thread (no audio-thread allocations).
- DSP shell: drive → low-pass → dry/wet mix. Audio thread stays allocation-free; parameters via APVTS.
- Formats: AU, VST3, Standalone.
- Build system: JUCE CMake; Xcode or CLI.
- Targets macOS 12+, C++17.

## Source layout

```text
plugins/juce_ui_demo/
  CMakeLists.txt
  Source/
    PluginProcessor.{h,cpp}   // DSP + parameters (APVTS)
    PluginEditor.{h,cpp}      // Custom dials, envelope, meter
```

## Build (CLI)

```bash
cd plugins/juce_ui_demo
# Point JUCE_DIR at your JUCE checkout (submodule or sibling). Default: ./JUCE
cmake -B build -G Xcode -DJUCE_DIR=/path/to/JUCE
cmake --build build --config Debug      # or Release
```

Outputs:

- Standalone: `build/Debug/MAStyle JUCE Demo.app`
- VST3: `build/Debug/MAStyle JUCE Demo.vst3`
- AU: `build/Debug/MAStyle JUCE Demo.component`

Sidecars:

- Writes to `~/music-advisor/data/features_output/juce_probe/<track>/<timestamp>/juce_probe_features.json` with RMS/peak/crest metrics.

## Packaging

```bash
cmake --build build --config Release
cmake --install build --config Release --prefix dist
# zip dist or copy .vst3/.component to user plugin folders for testing
```

## Streamlined flow (presets + install)

```bash
cd plugins/juce_ui_demo
# Configure & build universal (arm64+x86_64) using presets (adjust JUCE_DIR in CMakePresets.json if needed):
cmake --preset juce-universal
cmake --build --preset juce-universal-build

# Install AU/VST3 to user root plugin folders (no vendor subfolder):
./scripts/install_root.sh Debug   # or Release

# If a host doesn’t see it and you want a targeted refresh (avoid full AU cache wipe):
# pluginkit -m -r ~/Library/Audio/Plug-Ins/Components/MAStyle\ JUCE\ Demo.component
# killall -9 AudioComponentRegistrar 2>/dev/null || true
# Then rescan only this plugin in the host.
```

If Ninja/PCH ever reports missing system headers (e.g., `<algorithm>`), verify Xcode is selected (`xcode-select -p`) and that `CMAKE_OSX_SYSROOT` in `CMakePresets.json` matches your Xcode SDK path:
`/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`.
If you hit PCH-related Objective-C errors in JUCE modules, PCH is disabled in this target; just rebuild (no manual PCH tweaks needed).

## Dev notes

- Audio thread: no allocations; uses APVTS parameters.
- Use AudioPluginHost/Logic to audition; tweak dials and envelope to see vector UI respond.
- Snapshot button writes sidecars; text fields tag track/session/host.
- Serves as a baseline for more advanced controls (knobs, sliders, sequencer/envelope widgets).
