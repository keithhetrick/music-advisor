#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_extra/juce_gui_extra.h>
#include "GuiStyle.h"

class StepSequencerView : public juce::Component {
public:
  StepSequencerView(juce::AudioProcessorValueTreeState &vts,
                    const std::vector<juce::RangedAudioParameter *> &params);
  void paint(juce::Graphics &g) override;
  void resized() override;

private:
  struct StepWidget {
    std::unique_ptr<juce::Slider> slider;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>
        attach;
  };

  std::vector<StepWidget> steps;
};
