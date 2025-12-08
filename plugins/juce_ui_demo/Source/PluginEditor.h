#pragma once

#include "PluginProcessor.h"
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_extra/juce_gui_extra.h>

#include "gui/controls/Dial.h"
#include "gui/controls/HaloKnob.h"
#include "gui/controls/MiniEnvelope.h"
#include "gui/controls/SimpleMeter.h"
#include "gui/controls/StepSequencerView.h"
#include "gui/controls/AnimatedSvgBadge.h"
#include "gui/controls/ArcSlider.h"

class MAStyleJuceDemoAudioProcessorEditor : public juce::AudioProcessorEditor {
public:
  explicit MAStyleJuceDemoAudioProcessorEditor(MAStyleJuceDemoAudioProcessor &);
  ~MAStyleJuceDemoAudioProcessorEditor() override = default;

  void paint(juce::Graphics &) override;
  void resized() override;

private:
  MAStyleJuceDemoAudioProcessor &processorRef;
  juce::UndoManager um;
  juce::TextEditor trackId, sessionId, hostField;
  juce::TextButton snapshotButton{"Snapshot Sidecar"};

  HaloKnob driveDial;
  Dial mixDial;
  Dial cutoffDial;
  Dial resoDial;
  ArcSlider toneDial;
  MiniEnvelope envView;
  SimpleMeter meter;
  StepSequencerView seqView;
  AnimatedSvgBadge badge;

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(
      MAStyleJuceDemoAudioProcessorEditor)
};
