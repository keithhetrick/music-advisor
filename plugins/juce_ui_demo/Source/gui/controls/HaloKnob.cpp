#include "HaloKnob.h"

HaloKnob::HaloKnob(juce::AudioProcessorValueTreeState &vts,
                   juce::RangedAudioParameter &param) {
  slider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
  slider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
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
}

void HaloKnob::paint(juce::Graphics &g) {
  auto bounds = getLocalBounds().toFloat();
  auto inner = bounds.reduced(8.0f);
  auto center = inner.getCentre();
  auto radius = juce::jmin(inner.getWidth(), inner.getHeight()) * 0.5f - 6.0f;

  g.setColour(guiPanel());
  g.fillRoundedRectangle(bounds, 8.0f);
  g.setColour(guiBorder());
  g.drawRoundedRectangle(bounds, 8.0f, 1.2f);

  g.setColour(guiHalo());
  g.fillEllipse(center.x - radius - 6.0f, center.y - radius - 6.0f,
                2 * (radius + 6.0f), 2 * (radius + 6.0f));

  auto knobArea = inner.reduced(12.0f);
  auto angle = juce::MathConstants<float>::pi * 1.2f;
  auto start = juce::MathConstants<float>::pi * 1.7f;
  auto end = start + (float)slider.getValue() / (float)slider.getMaximum() * angle;
  juce::Path arc;
  arc.addArc(knobArea.getX(), knobArea.getY(), knobArea.getWidth(),
             knobArea.getHeight(), start, end, true);
  g.setColour(guiAccent());
  g.strokePath(arc, juce::PathStrokeType(2.5f));
}

void HaloKnob::resized() {
  auto r = getLocalBounds();
  label.setBounds(r.removeFromTop(20));
  slider.setBounds(r.reduced(6));
}
