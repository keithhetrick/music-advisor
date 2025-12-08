#include "Dial.h"

Dial::Dial(juce::AudioProcessorValueTreeState &vts,
           juce::RangedAudioParameter &param, juce::UndoManager *um) {
  juce::ignoreUnused(um);
  slider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
  slider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
  slider.setColour(juce::Slider::rotarySliderFillColourId, guiAccent());
  slider.setColour(juce::Slider::rotarySliderOutlineColourId, guiBorder());
  addAndMakeVisible(slider);

  label.setText(param.getName(32), juce::dontSendNotification);
  label.setJustificationType(juce::Justification::centred);
  label.setColour(juce::Label::textColourId, juce::Colours::white);
  addAndMakeVisible(label);

  attachment =
      std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
          vts, param.paramID, slider);
}

void Dial::paint(juce::Graphics &g) {
  auto bounds = getLocalBounds().toFloat();
  g.setColour(guiPanel().withAlpha(0.6f));
  g.fillRoundedRectangle(bounds, 6.0f);
  g.setColour(guiBorder());
  g.drawRoundedRectangle(bounds, 6.0f, 1.0f);
}

void Dial::resized() {
  auto r = getLocalBounds();
  label.setBounds(r.removeFromTop(20));
  slider.setBounds(r.reduced(6));
}
