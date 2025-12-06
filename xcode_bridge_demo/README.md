# Xcode bridge demo (no JUCE required)

Use this tiny macOS GUI app to prove the VS Code → CMake → Xcode workflow before wiring JUCE.

## Build and run

```bash
cd xcode_bridge_demo
cmake -S . -B build -G Xcode
cmake --build build --config Debug
open build/Debug/Xcode\\ Bridge\\ Demo.app
# or open build/XcodeBridgeDemo.xcodeproj in Xcode and run from there
```

The window reads “If you can see this window, the bridge works.” and the OK button exits. No external dependencies beyond the macOS SDK. If this builds, the same workflow will work once JUCE is available for the plugin.***
