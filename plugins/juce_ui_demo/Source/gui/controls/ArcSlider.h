#pragma once

#include <juce_gui_extra/juce_gui_extra.h>
#include <juce_audio_processors/juce_audio_processors.h>
#include "GuiStyle.h"

// Animated arc slider: shows value as a sweeping arc with a moving head.
class ArcSlider : public juce::Component, private juce::Timer {
public:
  ArcSlider(juce::AudioProcessorValueTreeState &vts,
            juce::RangedAudioParameter &param);
  void paint(juce::Graphics &g) override;
  void resized() override;

private:
  void timerCallback() override;
  juce::Slider slider;
  juce::Label label;
  std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>
      attachment;
  float phase = 0.0f;
};
