cmake_minimum_required(VERSION 3.21)

project(MAStyleJuceDemo VERSION 0.1.1)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_OSX_DEPLOYMENT_TARGET "12.0" CACHE STRING "" FORCE)
# Build universal so AU/VST3 show up on Apple Silicon and Intel hosts.
set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "" FORCE)

option(MASTYLE_DEV_STANDALONE "Build only the Standalone target for fast dev iteration" OFF)

# Point this to your JUCE checkout (submodule or sibling).
set(JUCE_DIR "${CMAKE_SOURCE_DIR}/JUCE" CACHE PATH "Path to the JUCE repository")
if(NOT EXISTS "${JUCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "JUCE not found at ${JUCE_DIR}. Set JUCE_DIR to your JUCE checkout (git submodule or sibling).")
endif()

add_subdirectory("${JUCE_DIR}" JUCE)

set(MASTYLE_PLUGIN_FORMATS "AU;VST3;Standalone")
if(MASTYLE_DEV_STANDALONE)
    set(MASTYLE_PLUGIN_FORMATS "Standalone")
endif()

juce_add_plugin(MAStyleJuceDemo
    COMPANY_NAME             "Bellweather Studios"
    BUNDLE_ID                "com.bellweatherstudios.mastyle.demo"
    PLUGIN_NAME              "MAStyle JUCE Demo"
    PLUGIN_CODE              MsUi
    PLUGIN_MANUFACTURER_CODE Bwsd
    IS_SYNTH                 FALSE
    NEEDS_MIDI_INPUT         FALSE
    NEEDS_MIDI_OUTPUT        FALSE
    IS_MIDI_EFFECT           FALSE
    FORMATS                  ${MASTYLE_PLUGIN_FORMATS}
    PRODUCT_NAME             "MAStyle JUCE Demo")

target_sources(MAStyleJuceDemo PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginProcessor.h
    Source/PluginEditor.cpp
    Source/PluginEditor.h
    Source/gui/controls/GuiStyle.h
    Source/gui/controls/Dial.cpp
    Source/gui/controls/Dial.h
    Source/gui/controls/MiniEnvelope.cpp
    Source/gui/controls/MiniEnvelope.h
    Source/gui/controls/SimpleMeter.cpp
    Source/gui/controls/SimpleMeter.h
    Source/gui/controls/HaloKnob.cpp
    Source/gui/controls/HaloKnob.h
    Source/gui/controls/StepSequencerView.cpp
    Source/gui/controls/StepSequencerView.h
    Source/gui/controls/AnimatedSvgBadge.cpp
    Source/gui/controls/AnimatedSvgBadge.h
    Source/gui/controls/ArcSlider.cpp
    Source/gui/controls/ArcSlider.h
)

target_compile_definitions(MAStyleJuceDemo
    PRIVATE
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_MODAL_LOOPS_PERMITTED=0
        JUCE_VST3_CAN_REPLACE_VST2=0
        JUCE_COMPANY_CODE=Bwsd)

target_link_libraries(MAStyleJuceDemo PRIVATE
    juce::juce_audio_utils
    juce::juce_dsp
    juce::juce_gui_extra
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
    juce::juce_recommended_lto_flags)
