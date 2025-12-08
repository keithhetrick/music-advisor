#include "ArcSlider.h"

ArcSlider::ArcSlider(juce::AudioProcessorValueTreeState &vts,
                     juce::RangedAudioParameter &param) {
  slider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
  slider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
  slider.setColour(juce::Slider::rotarySliderFillColourId, guiAccent());
  slider.setColour(juce::Slider::rotarySliderOutlineColourId, guiBorder());
  slider.setPopupDisplayEnabled(true, true, nullptr);
  addAndMakeVisible(slider);

  label.setText(param.getName(32), juce::dontSendNotification);
  label.setJustificationType(juce::Justification::centred);
  label.setColour(juce::Label::textColourId, juce::Colours::white);
  addAndMakeVisible(label);

  attachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
      vts, param.paramID, slider);

  startTimerHz(30);
}

void ArcSlider::paint(juce::Graphics &g) {
  auto b = getLocalBounds().toFloat().reduced(6.0f);
  auto inner = b.reduced(10.0f);
  auto centre = inner.getCentre();
  auto radius = juce::jmin(inner.getWidth(), inner.getHeight()) * 0.5f - 8.0f;

  g.setColour(guiPanel());
  g.fillRoundedRectangle(b, 10.0f);
  g.setColour(guiBorder());
  g.drawRoundedRectangle(b, 10.0f, 1.0f);

  // Arc background
  juce::Path bg;
  bg.addCentredArc(centre.x, centre.y, radius, radius,
                   0.0f,
                   juce::MathConstants<float>::pi * 1.1f,
                   juce::MathConstants<float>::pi * 1.9f,
                   true);
  g.setColour(guiBorder().withAlpha(0.4f));
  g.strokePath(bg, juce::PathStrokeType(3.0f));

  // Value arc
  const auto norm = (float)slider.getValue() / (float)slider.getMaximum();
  const auto start = juce::MathConstants<float>::pi * 1.1f;
  const auto end = start + norm * juce::MathConstants<float>::pi * 0.8f;
  juce::Path arc;
  arc.addCentredArc(centre.x, centre.y, radius, radius, 0.0f, start, end, true);
  g.setColour(guiAccent());
  g.strokePath(arc, juce::PathStrokeType(4.0f, juce::PathStrokeType::curved));

  // Moving head
  const auto headAngle = end;
  juce::Point<float> head(centre.x + radius * std::cos(headAngle),
                          centre.y + radius * std::sin(headAngle));
  auto headRadius = 5.0f + 1.0f * std::sin(phase);
  g.setColour(guiHalo());
  g.fillEllipse(head.x - headRadius * 1.5f, head.y - headRadius * 1.5f,
                headRadius * 3.0f, headRadius * 3.0f);
  g.setColour(juce::Colours::white);
  g.fillEllipse(head.x - headRadius, head.y - headRadius,
                headRadius * 2.0f, headRadius * 2.0f);
}

void ArcSlider::resized() {
  auto r = getLocalBounds();
  label.setBounds(r.removeFromTop(18));
  slider.setBounds(r);
}

void ArcSlider::timerCallback() {
  phase += 0.12f;
  repaint();
}
