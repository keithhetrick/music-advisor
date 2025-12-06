#pragma once

#include <juce_gui_extra/juce_gui_extra.h>

#include "PluginProcessor.h"

class MusicAdvisorProbeAudioProcessorEditor : public juce::AudioProcessorEditor,
                                              private juce::Timer
{
public:
    explicit MusicAdvisorProbeAudioProcessorEditor(MusicAdvisorProbeAudioProcessor&);
    ~MusicAdvisorProbeAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    void triggerSnapshot();
    void timerCallback() override;

    MusicAdvisorProbeAudioProcessor& processor;

    juce::Label titleLabel;
    juce::Label trackLabel;
    juce::Label sessionLabel;
    juce::Label dataRootLabel;
    juce::Label statusLabel;

    juce::TextEditor trackField;
    juce::TextEditor sessionField;
    juce::TextEditor dataRootField;

    juce::TextButton snapshotButton{"Write Snapshot"};
    juce::ToggleButton captureToggle{"Capture"};

    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> captureAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MusicAdvisorProbeAudioProcessorEditor)
};
