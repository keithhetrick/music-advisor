# Xcode bridge (no JUCE required)

What it is  
- A minimal macOS GUI app + CMake project that proves the VS Code → CMake → Xcode toolchain works on this machine.  
- All artifacts (build + DerivedData) stay inside `tools/xcode_bridge/build` for easy cleanup/portability.

What problem it solves  
- Validates Xcode/Clang, CMake, and the `-G Xcode` generator before touching JUCE or production hosts.  
- Provides a drop-in template you can sparse-checkout and run anywhere to confirm the macOS toolchain is sane.

How to build and run

```bash
cd tools/xcode_bridge
./build_debug.sh
open build/Debug/Xcode\ Bridge\ Demo.app
# or open build/XcodeBridgeDemo.xcodeproj in Xcode and Run
```

What to expect  
- A small window that reads: “If you can see this window, the bridge works.” OK exits.
- No external deps beyond Xcode/macOS SDK; works offline once Xcode is installed.

Notes  
- If you sparse-checkout: `git sparse-checkout set tools/xcode_bridge`.  
- If you want to wipe artifacts: `rm -rf tools/xcode_bridge/build`.
