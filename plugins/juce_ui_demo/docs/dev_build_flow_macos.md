# Fast macOS Dev Loop (JUCE + CMake + Ninja)

Goal: edit in VS Code, build fast with Ninja, run the Standalone for UI iteration, keep Xcode for signing/profiling.

## Build directories

- `plugins/juce_ui_demo/build-ninja`: Ninja, Debug, Standalone-only (fastest loop).
- `plugins/juce_ui_demo/build-xcode`: Xcode generator, RelWithDebInfo (packaging/profiling).
- Legacy Makefiles build remains at `plugins/juce_ui_demo/build` if you prefer.

## Configure & build (Ninja, fast loop)

```bash
cd plugins/juce_ui_demo
cmake --preset juce-ninja
cmake --build --preset juce-ninja-build
# Run the Standalone:
open build-ninja/MAStyleJuceDemo_artefacts/Standalone/MAStyle\ JUCE\ Demo.app
```

## Configure & build (Xcode, packaging)

```bash
cd plugins/juce_ui_demo
cmake --preset juce-xcode
cmake --build --preset juce-xcode-build
```

## Install AU/VST3 (root paths)

```bash
cd plugins/juce_ui_demo
./scripts/install_root.sh Debug   # or Release/RelWithDebInfo
```

## Targeted AU refresh (avoid full cache wipe)

```bash
pluginkit -m -r ~/Library/Audio/Plug-Ins/Components/MAStyle\ JUCE\ Demo.component
killall -9 AudioComponentRegistrar 2>/dev/null || true
# Then rescan this plugin in the host.
```

## Notes

- Enable dev Standalone only via `-DMASTYLE_DEV_STANDALONE=ON` (preset already sets this for Ninja).
- Precompiled headers are disabled here to avoid ObjC/PCH conflicts; rebuilds remain clean under Ninja.
- C++17, macOS 12+ target, universal (arm64+x86_64).
