#pragma once

#include <juce_gui_extra/juce_gui_extra.h>
#include "GuiStyle.h"

class SimpleMeter : public juce::Component, private juce::Timer {
public:
  explicit SimpleMeter(std::function<float()> rmsProvider);
  void paint(juce::Graphics &g) override;

private:
  void timerCallback() override;
  std::function<float()> getRms;
  float meterValue = 0.0f;
};
