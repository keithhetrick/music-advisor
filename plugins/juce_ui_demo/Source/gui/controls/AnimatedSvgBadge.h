#pragma once

#include <juce_gui_extra/juce_gui_extra.h>
#include "GuiStyle.h"

class AnimatedSvgBadge : public juce::Component, private juce::Timer {
public:
  AnimatedSvgBadge();
  void paint(juce::Graphics &g) override;
  void resized() override;

private:
  void timerCallback() override;
  std::unique_ptr<juce::Drawable> drawable;
  float phase = 0.0f;
};
