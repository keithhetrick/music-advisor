cmake_minimum_required(VERSION 3.21)

project(XcodeBridgeDemo LANGUAGES C CXX OBJC OBJCXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Simple macOS GUI app to validate the VS Code → CMake → Xcode bridge.
add_executable(XcodeBridgeDemo MACOSX_BUNDLE
    src/main.mm
)

set_target_properties(XcodeBridgeDemo PROPERTIES
    MACOSX_BUNDLE_GUI_IDENTIFIER "com.withrowstreet.xcodebridgedemo"
    MACOSX_BUNDLE_BUNDLE_NAME "Xcode Bridge Demo"
    MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/cmake/Info.plist.in"
)

target_link_libraries(XcodeBridgeDemo
    "-framework AppKit"
)
