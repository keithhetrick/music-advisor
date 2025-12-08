#include "MiniEnvelope.h"

MiniEnvelope::MiniEnvelope(juce::AudioProcessorValueTreeState &vts,
                           juce::RangedAudioParameter &attack,
                           juce::RangedAudioParameter &release,
                           juce::UndoManager *um)
    : processorState(vts) {
  juce::ignoreUnused(um);
  attackSlider.setSliderStyle(juce::Slider::LinearVertical);
  attackSlider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
  releaseSlider.setSliderStyle(juce::Slider::LinearVertical);
  releaseSlider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
  addAndMakeVisible(attackSlider);
  addAndMakeVisible(releaseSlider);
  attackAttach =
      std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
          processorState, attack.paramID, attackSlider);
  releaseAttach =
      std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
          processorState, release.paramID, releaseSlider);
  startTimerHz(30);
}

void MiniEnvelope::paint(juce::Graphics &g) {
  g.fillAll(guiPanel());
  g.setColour(guiBorder());
  g.drawRoundedRectangle(getLocalBounds().toFloat(), 6.0f, 1.0f);

  auto atk = (float)attackSlider.getValue();
  auto rel = (float)releaseSlider.getValue();
  auto width = (float)getWidth();
  auto height = (float)getHeight();
  float atkX = juce::jmap(atk, 1.0f, 500.0f, 0.05f * width, 0.45f * width);
  float relX = juce::jmap(rel, 5.0f, 1000.0f, 0.55f * width, 0.95f * width);

  juce::Path env;
  env.startNewSubPath(0.05f * width, height * 0.9f);
  env.lineTo(atkX, height * 0.1f);
  env.lineTo(relX, height * 0.6f);
  env.lineTo(width * 0.97f, height * 0.9f);

  g.setColour(guiAccent());
  g.strokePath(env, juce::PathStrokeType(2.0f));
}

void MiniEnvelope::resized() {
  auto area = getLocalBounds().reduced(6);
  auto half = area.proportionOfWidth(0.5f);
  attackSlider.setBounds(area.removeFromLeft((int)half));
  releaseSlider.setBounds(area);
}

void MiniEnvelope::timerCallback() { repaint(); }
