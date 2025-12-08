#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_extra/juce_gui_extra.h>
#include "GuiStyle.h"

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
