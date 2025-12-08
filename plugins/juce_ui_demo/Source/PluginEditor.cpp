#include "PluginEditor.h"
#include "PluginProcessor.h"

namespace {
auto panelColor() { return juce::Colour::fromRGB(20, 26, 33); }
auto accent() { return juce::Colour::fromRGB(65, 156, 255); }
auto border() { return juce::Colour::fromRGB(60, 70, 80); }
} // namespace

Dial::Dial(juce::AudioProcessorValueTreeState &vts,
           juce::RangedAudioParameter &param, juce::UndoManager *um) {
  juce::ignoreUnused(um);
  slider.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
  slider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
  slider.setColour(juce::Slider::rotarySliderFillColourId, accent());
  slider.setColour(juce::Slider::rotarySliderOutlineColourId, border());
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
  g.setColour(panelColor().withAlpha(0.6f));
  g.fillRoundedRectangle(bounds, 6.0f);
  g.setColour(border());
  g.drawRoundedRectangle(bounds, 6.0f, 1.0f);
}

void Dial::resized() {
  auto r = getLocalBounds();
  label.setBounds(r.removeFromTop(20));
  slider.setBounds(r.reduced(6));
}

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
  // Bind into the shared APVTS so we avoid touching parameters directly.
  attackAttach =
      std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
          processorState, attack.paramID, attackSlider);
  releaseAttach =
      std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
          processorState, release.paramID, releaseSlider);
  startTimerHz(30);
}

void MiniEnvelope::paint(juce::Graphics &g) {
  g.fillAll(panelColor());
  g.setColour(border());
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

  g.setColour(accent());
  g.strokePath(env, juce::PathStrokeType(2.0f));
}

void MiniEnvelope::resized() {
  auto area = getLocalBounds().reduced(6);
  auto half = area.proportionOfWidth(0.5f);
  attackSlider.setBounds(area.removeFromLeft((int)half));
  releaseSlider.setBounds(area);
}

void MiniEnvelope::timerCallback() { repaint(); }

SimpleMeter::SimpleMeter(std::function<float()> rmsProvider)
    : getRms(std::move(rmsProvider)) {
  startTimerHz(30);
}

void SimpleMeter::paint(juce::Graphics &g) {
  auto bounds = getLocalBounds().toFloat();
  g.setColour(panelColor().withAlpha(0.6f));
  g.fillRoundedRectangle(bounds, 6.0f);
  g.setColour(border());
  g.drawRoundedRectangle(bounds, 6.0f, 1.0f);

  auto bar = bounds.reduced(6.0f);
  bar.removeFromLeft(bar.getWidth() * (1.0f - meterValue));
  g.setColour(accent());
  g.fillRoundedRectangle(bar, 4.0f);
}

void SimpleMeter::timerCallback() {
  meterValue = juce::jlimit(0.0f, 1.0f, getRms());
  repaint();
}

MAStyleJuceDemoAudioProcessorEditor::MAStyleJuceDemoAudioProcessorEditor(
    MAStyleJuceDemoAudioProcessor &p)
    : AudioProcessorEditor(&p), processorRef(p),
      driveDial(p.getValueTreeState(),
                *p.getValueTreeState().getParameter("drive"), &um),
      mixDial(p.getValueTreeState(), *p.getValueTreeState().getParameter("mix"),
              &um),
      cutoffDial(p.getValueTreeState(),
                 *p.getValueTreeState().getParameter("cutoff"), &um),
      resoDial(p.getValueTreeState(),
               *p.getValueTreeState().getParameter("resonance"), &um),
      envView(p.getValueTreeState(),
              *p.getValueTreeState().getParameter("attack"),
              *p.getValueTreeState().getParameter("release"), &um),
      meter([&]() { return processorRef.getLastRms(); }) {
  trackId.setText("track-1");
  sessionId.setText("session-1");
  hostField.setText("Logic");
  for (auto *te : {&trackId, &sessionId, &hostField}) {
    te->setColour(juce::TextEditor::backgroundColourId, panelColor());
    te->setColour(juce::TextEditor::textColourId, juce::Colours::white);
    te->setColour(juce::TextEditor::outlineColourId, border());
    addAndMakeVisible(te);
  }
  snapshotButton.onClick = [this]() {
    SidecarMeta meta;
    meta.trackId = trackId.getText();
    meta.sessionId = sessionId.getText();
    meta.host = hostField.getText();
    processorRef.requestSidecar(meta);
  };
  snapshotButton.setColour(juce::TextButton::buttonColourId, accent());
  snapshotButton.setColour(juce::TextButton::textColourOffId,
                           juce::Colours::white);
  addAndMakeVisible(snapshotButton);

  addAndMakeVisible(driveDial);
  addAndMakeVisible(mixDial);
  addAndMakeVisible(cutoffDial);
  addAndMakeVisible(resoDial);
  addAndMakeVisible(envView);
  addAndMakeVisible(meter);
  setResizable(true, true);
  setSize(620, 360);
}

void MAStyleJuceDemoAudioProcessorEditor::paint(juce::Graphics &g) {
  g.fillAll(juce::Colour::fromRGB(12, 16, 20));
  auto area = getLocalBounds().toFloat().reduced(10.0f);
  g.setColour(border());
  g.drawRoundedRectangle(area, 12.0f, 1.2f);
  g.setColour(juce::Colours::white);
  juce::FontOptions opts;
  opts = opts.withHeight(16.0f);
  juce::Font titleFont(opts);
  titleFont.setBold(true);
  g.setFont(titleFont);
  g.drawText("MAStyle JUCE UI Demo", 12, 6, 300, 20, juce::Justification::left);
}

void MAStyleJuceDemoAudioProcessorEditor::resized() {
  auto area = getLocalBounds().reduced(16);
  auto header = area.removeFromTop(50);
  auto third = header.getWidth() / 3;
  trackId.setBounds(header.removeFromLeft(third).reduced(4));
  sessionId.setBounds(header.removeFromLeft(third).reduced(4));
  hostField.setBounds(header.reduced(4));

  auto snapArea = area.removeFromTop(40);
  snapshotButton.setBounds(snapArea.removeFromLeft(200));

  auto topRow = area.removeFromTop(160);
  driveDial.setBounds(topRow.removeFromLeft(topRow.getWidth() / 4).reduced(6));
  mixDial.setBounds(topRow.removeFromLeft(topRow.getWidth() / 3).reduced(6));
  cutoffDial.setBounds(topRow.removeFromLeft(topRow.getWidth() / 2).reduced(6));
  resoDial.setBounds(topRow.reduced(6));

  auto bottom = area.reduced(6);
  auto left = bottom.removeFromLeft(static_cast<int>(bottom.getWidth() * 0.65f));
  envView.setBounds(left);
  meter.setBounds(bottom.reduced(6));
}
