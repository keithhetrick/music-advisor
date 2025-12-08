#include "SimpleMeter.h"

SimpleMeter::SimpleMeter(std::function<float()> rmsProvider)
    : getRms(std::move(rmsProvider)) {
  startTimerHz(30);
}

void SimpleMeter::paint(juce::Graphics &g) {
  auto bounds = getLocalBounds().toFloat();
  g.setColour(guiPanel().withAlpha(0.6f));
  g.fillRoundedRectangle(bounds, 6.0f);
  g.setColour(guiBorder());
  g.drawRoundedRectangle(bounds, 6.0f, 1.0f);

  auto bar = bounds.reduced(6.0f);
  bar.removeFromLeft(bar.getWidth() * (1.0f - meterValue));
  g.setColour(guiAccent());
  g.fillRoundedRectangle(bar, 4.0f);
}

void SimpleMeter::timerCallback() {
  meterValue = juce::jlimit(0.0f, 1.0f, getRms());
  repaint();
}
