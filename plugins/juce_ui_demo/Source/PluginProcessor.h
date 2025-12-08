#pragma once

#include <array>
#include "FeatureCollector.h"
#include "SidecarWriter.h"
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_dsp/juce_dsp.h>

class MAStyleJuceDemoAudioProcessor : public juce::AudioProcessor {
public:
  MAStyleJuceDemoAudioProcessor();
  ~MAStyleJuceDemoAudioProcessor() override;

  // AudioProcessor
  void prepareToPlay(double sampleRate, int samplesPerBlock) override;
  void releaseResources() override {}
  bool isBusesLayoutSupported(const BusesLayout &layouts) const override;
  void processBlock(juce::AudioBuffer<float> &, juce::MidiBuffer &) override;

  juce::AudioProcessorEditor *createEditor() override;
  bool hasEditor() const override { return true; }

  const juce::String getName() const override { return "MAStyleJuceDemo"; }
  bool acceptsMidi() const override { return false; }
  bool producesMidi() const override { return false; }
  bool isMidiEffect() const override { return false; }
  double getTailLengthSeconds() const override { return 0.0; }

  int getNumPrograms() override { return 1; }
  int getCurrentProgram() override { return 0; }
  void setCurrentProgram(int) override {}
  const juce::String getProgramName(int) override { return {}; }
  void changeProgramName(int, const juce::String &) override {}

  void getStateInformation(juce::MemoryBlock &destData) override;
  void setStateInformation(const void *data, int sizeInBytes) override;

  juce::AudioProcessorValueTreeState &getValueTreeState() { return state; }
  float getLastRms() const { return lastRms; }
  ProbeStats getStatsAndReset() { return collector.snapshotAndReset(); }
  void requestSidecar(const SidecarMeta &meta);

private:
  float onePoleToneSample(float x, float fc) noexcept;

  juce::AudioProcessorValueTreeState state;
  juce::dsp::DryWetMixer<float> dryWet;
  juce::LinearSmoothedValue<float> rmsMeter;
  float lastRms = 0.0f;
  FeatureCollector collector;
  SidecarWriter writer;
  juce::ThreadPool pool{1};
  float toneStateL{0.0f}, toneStateR{0.0f};
  double stepPhase{0.0};
  double stepDeltaPerSample{0.0};
  static constexpr int numSteps = 8;
  std::array<std::atomic<float> *, numSteps> stepParams{};

  juce::AudioProcessorValueTreeState::ParameterLayout createLayout();

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MAStyleJuceDemoAudioProcessor)
};
