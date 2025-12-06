cmake_minimum_required(VERSION 3.21)

project(MusicAdvisorProbe VERSION 0.1.0)

# JUCE expects C++17+; keep the standard consistent with the rest of the repo.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Allow callers to point at an existing JUCE checkout (submodule or sibling).
set(JUCE_DIR "${CMAKE_SOURCE_DIR}/JUCE" CACHE PATH "Path to the JUCE repository")
if(NOT EXISTS "${JUCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "JUCE not found at ${JUCE_DIR}. Set JUCE_DIR to your JUCE checkout (git submodule or sibling).")
endif()

add_subdirectory("${JUCE_DIR}" JUCE)

juce_add_plugin(MusicAdvisorProbe
    COMPANY_NAME        "WithrowStreet"
    BUNDLE_ID           "com.withrowstreet.musicadvisor.probe"
    PLUGIN_NAME         "Music Advisor Probe"
    PLUGIN_CODE         MaPr
    IS_SYNTH            FALSE
    NEEDS_MIDI_INPUT    FALSE
    NEEDS_MIDI_OUTPUT   FALSE
    IS_MIDI_EFFECT      FALSE
    FORMATS             AU VST3 Standalone
    PRODUCT_NAME        "Music Advisor Probe")

target_sources(MusicAdvisorProbe PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginProcessor.h
    Source/PluginEditor.cpp
    Source/PluginEditor.h
    Source/dsp/FeatureCollector.cpp
    Source/dsp/FeatureCollector.h)

target_compile_definitions(MusicAdvisorProbe
    PRIVATE
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_VST3_CAN_REPLACE_VST2=0)

target_link_libraries(MusicAdvisorProbe
    PRIVATE
        juce::juce_audio_utils
        juce::juce_dsp
        juce::juce_gui_extra
        juce::juce_audio_devices
        juce::juce_audio_basics
        juce::juce_audio_processors
        juce::juce_graphics
        juce::juce_core)

if(APPLE)
    # Keep bundle location predictable for copies into AU/VST3 folders.
    set_target_properties(MusicAdvisorProbe PROPERTIES
        XCODE_ATTRIBUTE_CODE_SIGN_IDENTITY "-"
        XCODE_ATTRIBUTE_DEVELOPMENT_TEAM ""
        XCODE_ATTRIBUTE_MACOSX_DEPLOYMENT_TARGET "11.0")
endif()
