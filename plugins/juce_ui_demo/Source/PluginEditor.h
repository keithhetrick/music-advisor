#pragma once

#include "PluginProcessor.h"
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_extra/juce_gui_extra.h>

class Dial : public juce::Component {
public:
  Dial(juce::AudioProcessorValueTreeState &vts,
       juce::RangedAudioParameter &param, juce::UndoManager *um);
  void paint(juce::Graphics &g) override;
  void resized() override;

private:
  juce::Slider slider;
  juce::Label label;
  std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>
      attachment;
};

class MiniEnvelope : public juce::Component, private juce::Timer {
public:
  MiniEnvelope(juce::AudioProcessorValueTreeState &vts,
               juce::RangedAudioParameter &attack,
               juce::RangedAudioParameter &release, juce::UndoManager *um);
  ~MiniEnvelope() override = default;
  void paint(juce::Graphics &g) override;
  void resized() override;

private:
  void timerCallback() override;
  juce::AudioProcessorValueTreeState &processorState;
  juce::Slider attackSlider, releaseSlider;
  std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>
      attackAttach, releaseAttach;
};

class SimpleMeter : public juce::Component, private juce::Timer {
public:
  explicit SimpleMeter(std::function<float()> rmsProvider);
  void paint(juce::Graphics &g) override;

private:
  void timerCallback() override;
  std::function<float()> getRms;
  float meterValue = 0.0f;
};

class MAStyleJuceDemoAudioProcessorEditor : public juce::AudioProcessorEditor {
public:
  explicit MAStyleJuceDemoAudioProcessorEditor(MAStyleJuceDemoAudioProcessor &);
  ~MAStyleJuceDemoAudioProcessorEditor() override = default;

  void paint(juce::Graphics &) override;
  void resized() override;

private:
  MAStyleJuceDemoAudioProcessor &processorRef;
  juce::UndoManager um;
  juce::TextEditor trackId, sessionId, hostField;
  juce::TextButton snapshotButton{"Snapshot Sidecar"};

  Dial driveDial;
  Dial mixDial;
  Dial cutoffDial;
  Dial resoDial;
  MiniEnvelope envView;
  SimpleMeter meter;

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(
      MAStyleJuceDemoAudioProcessorEditor)
};
