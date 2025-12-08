#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_extra/juce_gui_extra.h>
#include "GuiStyle.h"

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
