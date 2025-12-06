#include "PluginEditor.h"

#include <JuceHeader.h>
#include <cstdlib>

MusicAdvisorProbeAudioProcessorEditor::MusicAdvisorProbeAudioProcessorEditor(MusicAdvisorProbeAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processor(p)
{
    setSize(460, 260);

    titleLabel.setText("Music Advisor Probe", juce::dontSendNotification);
    titleLabel.setJustificationType(juce::Justification::centredLeft);
    titleLabel.setFont(juce::Font(18.0f, juce::Font::bold));

    trackLabel.setText("Track ID", juce::dontSendNotification);
    sessionLabel.setText("Session ID", juce::dontSendNotification);
    dataRootLabel.setText("MA_DATA_ROOT (optional)", juce::dontSendNotification);
    statusLabel.setJustificationType(juce::Justification::centredLeft);
    statusLabel.setText("Ready \u2022 Host: " + processor.getHostName(), juce::dontSendNotification);

    trackField.setText(processor.getTrackId(), juce::dontSendNotification);
    sessionField.setText(processor.getSessionId(), juce::dontSendNotification);
    if (auto* env = std::getenv("MA_DATA_ROOT"); env != nullptr)
        dataRootField.setText(env, juce::dontSendNotification);
    dataRootField.setTooltip("Override data root (defaults to ~/music-advisor/data or MA_DATA_ROOT).");

    snapshotButton.onClick = [this] { triggerSnapshot(); };

    captureAttachment = std::make_unique<juce::AudioProcessorValueTreeState::ButtonAttachment>(
        processor.getValueTreeState(), "capture_enabled", captureToggle);

    addAndMakeVisible(titleLabel);
    addAndMakeVisible(trackLabel);
    addAndMakeVisible(sessionLabel);
    addAndMakeVisible(dataRootLabel);
    addAndMakeVisible(statusLabel);
    addAndMakeVisible(trackField);
    addAndMakeVisible(sessionField);
    addAndMakeVisible(dataRootField);
    addAndMakeVisible(snapshotButton);
    addAndMakeVisible(captureToggle);

    startTimerHz(5);
}

void MusicAdvisorProbeAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkslategrey.darker(0.4f));
    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(14.0f));
}

void MusicAdvisorProbeAudioProcessorEditor::resized()
{
    auto area = getLocalBounds().reduced(12);
    auto header = area.removeFromTop(30);
    titleLabel.setBounds(header.removeFromLeft(area.getWidth() - 110));
    captureToggle.setBounds(header);

    const int rowHeight = 26;
    const int labelWidth = 140;
    const int spacing = 8;

    auto trackRow = area.removeFromTop(rowHeight);
    trackLabel.setBounds(trackRow.removeFromLeft(labelWidth));
    trackRow.removeFromLeft(spacing);
    trackField.setBounds(trackRow);

    area.removeFromTop(spacing);

    auto sessionRow = area.removeFromTop(rowHeight);
    sessionLabel.setBounds(sessionRow.removeFromLeft(labelWidth));
    sessionRow.removeFromLeft(spacing);
    sessionField.setBounds(sessionRow);

    area.removeFromTop(spacing);

    auto dataRow = area.removeFromTop(rowHeight);
    dataRootLabel.setBounds(dataRow.removeFromLeft(labelWidth));
    dataRow.removeFromLeft(spacing);
    dataRootField.setBounds(dataRow);

    area.removeFromTop(spacing);

    auto buttonRow = area.removeFromTop(rowHeight);
    snapshotButton.setBounds(buttonRow.removeFromLeft(160));
    buttonRow.removeFromLeft(spacing);
    statusLabel.setBounds(buttonRow);
}

void MusicAdvisorProbeAudioProcessorEditor::triggerSnapshot()
{
    snapshotButton.setEnabled(false);
    statusLabel.setText("Writing snapshot...", juce::dontSendNotification);

    processor.requestSnapshotFromUI(trackField.getText().trim(),
                                    sessionField.getText().trim(),
                                    dataRootField.getText().trim());

    snapshotButton.setEnabled(true);
}

void MusicAdvisorProbeAudioProcessorEditor::timerCallback()
{
    juce::String status;
    if (processor.isWritingSnapshot())
    {
        status = "Writing snapshot...";
    }
    else if (auto last = processor.getLastSnapshotPath(); last.isNotEmpty())
    {
        status = "Last: " + last;
    }
    else
    {
        status = "Ready • Host: " + processor.getHostName();
    }

    statusLabel.setText(status, juce::dontSendNotification);
}
