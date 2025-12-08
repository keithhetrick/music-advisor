#include "StepSequencerView.h"

StepSequencerView::StepSequencerView(
    juce::AudioProcessorValueTreeState &vts,
    const std::vector<juce::RangedAudioParameter *> &params) {
  steps.reserve(params.size());
  for (auto *p : params) {
    StepWidget w;
    w.slider = std::make_unique<juce::Slider>();
    w.slider->setSliderStyle(juce::Slider::LinearBarVertical);
    w.slider->setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
    w.slider->setColour(juce::Slider::trackColourId, guiAccent());
    w.slider->setColour(juce::Slider::thumbColourId, juce::Colours::white);
    addAndMakeVisible(*w.slider);
    w.attach = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        vts, p->paramID, *w.slider);
    steps.push_back(std::move(w));
  }
}

void StepSequencerView::paint(juce::Graphics &g) {
  g.fillAll(guiPanel());
  auto bounds = getLocalBounds().toFloat();
  g.setColour(guiBorder());
  g.drawRoundedRectangle(bounds, 8.0f, 1.0f);

  auto w = bounds.getWidth();
  auto h = bounds.getHeight();
  g.setColour(guiBorder().withAlpha(0.3f));
  for (int i = 1; i < 4; ++i) {
    auto y = bounds.getY() + i * h / 4.0f;
    g.drawLine(bounds.getX(), y, bounds.getRight(), y, 0.5f);
  }

  g.setColour(juce::Colours::white.withAlpha(0.7f));
  g.setFont(12.0f);
  for (size_t i = 0; i < steps.size(); ++i) {
    auto labelX = bounds.getX() + (i + 0.5f) * w / steps.size();
    g.drawText(juce::String((int)(i + 1)), (int)(labelX - 8), (int)(h - 18), 16,
               16, juce::Justification::centred);
  }
}

void StepSequencerView::resized() {
  auto area = getLocalBounds().reduced(6);
  if (steps.empty())
    return;
  auto stepWidth = area.getWidth() / (int)steps.size();
  for (size_t i = 0; i < steps.size(); ++i) {
    auto r = area.removeFromLeft(stepWidth);
    steps[i].slider->setBounds(r);
  }
}
