#include "PluginEditor.h"
#include "gui/controls/GuiStyle.h"
#include "PluginProcessor.h"

MAStyleJuceDemoAudioProcessorEditor::MAStyleJuceDemoAudioProcessorEditor(
    MAStyleJuceDemoAudioProcessor &p)
    : AudioProcessorEditor(&p), processorRef(p),
      driveDial(p.getValueTreeState(),
                *p.getValueTreeState().getParameter("drive")),
      mixDial(p.getValueTreeState(), *p.getValueTreeState().getParameter("mix"),
              &um),
      cutoffDial(p.getValueTreeState(),
                 *p.getValueTreeState().getParameter("cutoff"), &um),
      resoDial(p.getValueTreeState(),
               *p.getValueTreeState().getParameter("resonance"), &um),
      toneDial(p.getValueTreeState(),
               *p.getValueTreeState().getParameter("tone")),
      envView(p.getValueTreeState(),
              *p.getValueTreeState().getParameter("attack"),
              *p.getValueTreeState().getParameter("release"), &um),
      meter([&]() { return processorRef.getLastRms(); }),
      seqView(p.getValueTreeState(),
              {
                  p.getValueTreeState().getParameter("step1"),
                  p.getValueTreeState().getParameter("step2"),
                  p.getValueTreeState().getParameter("step3"),
                  p.getValueTreeState().getParameter("step4"),
                  p.getValueTreeState().getParameter("step5"),
                  p.getValueTreeState().getParameter("step6"),
                  p.getValueTreeState().getParameter("step7"),
                  p.getValueTreeState().getParameter("step8"),
              }) {
  trackId.setText("track-1");
  sessionId.setText("session-1");
  hostField.setText("Logic");
  for (auto *te : {&trackId, &sessionId, &hostField}) {
    te->setColour(juce::TextEditor::backgroundColourId, guiPanel());
    te->setColour(juce::TextEditor::textColourId, juce::Colours::white);
    te->setColour(juce::TextEditor::outlineColourId, guiBorder());
    addAndMakeVisible(te);
  }
  snapshotButton.onClick = [this]() {
    SidecarMeta meta;
    meta.trackId = trackId.getText();
    meta.sessionId = sessionId.getText();
    meta.host = hostField.getText();
    processorRef.requestSidecar(meta);
  };
  snapshotButton.setColour(juce::TextButton::buttonColourId, guiAccent());
  snapshotButton.setColour(juce::TextButton::textColourOffId,
                           juce::Colours::white);
  addAndMakeVisible(snapshotButton);

  addAndMakeVisible(driveDial);
  addAndMakeVisible(mixDial);
  addAndMakeVisible(cutoffDial);
  addAndMakeVisible(resoDial);
  addAndMakeVisible(toneDial);
  addAndMakeVisible(envView);
  addAndMakeVisible(meter);
  addAndMakeVisible(seqView);
  addAndMakeVisible(badge);
  setResizable(true, true);
  setSize(620, 360);
}

void MAStyleJuceDemoAudioProcessorEditor::paint(juce::Graphics &g) {
  g.fillAll(juce::Colour::fromRGB(12, 16, 20));
  auto area = getLocalBounds().toFloat().reduced(10.0f);
  g.setColour(guiBorder());
  g.drawRoundedRectangle(area, 12.0f, 1.2f);
  g.setColour(juce::Colours::white);
  juce::FontOptions fontOpts;
  fontOpts = fontOpts.withPointHeight(16.0f).withStyle("Bold");
  juce::Font titleFont(fontOpts);
  g.setFont(titleFont);
  g.drawText("MAStyle JUCE UI Demo", 12, 6, 300, 20, juce::Justification::left);
}

void MAStyleJuceDemoAudioProcessorEditor::resized() {
  auto area = getLocalBounds().reduced(16);
  auto header = area.removeFromTop(50);
  auto badgeSpace = header.removeFromRight(70);
  auto third = header.getWidth() / 3;
  trackId.setBounds(header.removeFromLeft(third).reduced(4));
  sessionId.setBounds(header.removeFromLeft(third).reduced(4));
  hostField.setBounds(header.reduced(4));
  badge.setBounds(badgeSpace.reduced(4));

  auto snapArea = area.removeFromTop(40);
  snapshotButton.setBounds(snapArea.removeFromLeft(200));

  auto topRow = area.removeFromTop(160);
  driveDial.setBounds(topRow.removeFromLeft(topRow.getWidth() / 4).reduced(6));
  mixDial.setBounds(topRow.removeFromLeft(topRow.getWidth() / 3).reduced(6));
  cutoffDial.setBounds(topRow.removeFromLeft(topRow.getWidth() / 2).reduced(6));
  resoDial.setBounds(topRow.reduced(6));

  auto secondRow = area.removeFromTop(120);
  toneDial.setBounds(secondRow.removeFromLeft(secondRow.getWidth() / 3).reduced(6));
  envView.setBounds(secondRow.removeFromLeft(secondRow.getWidth() / 2).reduced(6));
  meter.setBounds(secondRow.reduced(6));

  auto bottom = area.reduced(6);
  seqView.setBounds(bottom);
}
