# Xcode Bridge (VS Code → CMake → Xcode sanity check)

Purpose
- Prove the macOS toolchain works (Xcode/Clang + CMake with `-G Xcode`) before wiring JUCE or production hosts.
- Keep everything self-contained under `tools/xcode_bridge/`, including build outputs and DerivedData.

Location
- `tools/xcode_bridge/` (CMakeLists, main.mm, Info.plist template, build script).

Usage (turnkey)
```bash
cd tools/xcode_bridge
./build_debug.sh
open build/Debug/Xcode\ Bridge\ Demo.app
# or open build/XcodeBridgeDemo.xcodeproj in Xcode and Run
```

What you should see
- A simple window: “If you can see this window, the bridge works.” OK exits.
- No external deps beyond Xcode/macOS SDK; offline once Xcode is installed.
- Xcode does NOT need to be open; command-line builds (`./build_debug.sh` or `cmake --build …`) are enough once Xcode is installed/selected. Open Xcode only for IDE debugging or signing tweaks.

Artifacts
- Build products + DerivedData live in `tools/xcode_bridge/build/…` for easy cleanup (`rm -rf tools/xcode_bridge/build`).

When to use
- New machine / fresh Xcode install: confirm toolchain before JUCE/plugin or host work.
- Troubleshooting: if CMake+Xcode generation or clang fails, repro here first.

Sparse checkout
- `git sparse-checkout set tools/xcode_bridge` to grab only this bridge.***
