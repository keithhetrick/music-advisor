#include "PluginProcessor.h"
#include "PluginEditor.h"

MAStyleJuceDemoAudioProcessor::MAStyleJuceDemoAudioProcessor()
    : AudioProcessor(
          BusesProperties()
              .withInput("Input", juce::AudioChannelSet::stereo(), true)
              .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      state(*this, nullptr, "MASTYLE_DEMO", createLayout()) {
  rmsMeter.reset(48000.0, 0.05);
  // Cache raw step params for quick access.
  for (size_t i = 0; i < stepParams.size(); ++i)
    stepParams[i] = state.getRawParameterValue("step" + juce::String((int)i + 1));
}

MAStyleJuceDemoAudioProcessor::~MAStyleJuceDemoAudioProcessor() {
  pool.removeAllJobs(true, 1000);
}

juce::AudioProcessorValueTreeState::ParameterLayout
MAStyleJuceDemoAudioProcessor::createLayout() {
  using juce::ParameterID;
  std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      ParameterID{"drive", 1}, "Drive",
      juce::NormalisableRange<float>(0.0f, 24.0f), 6.0f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      ParameterID{"mix", 1}, "Mix",
      juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      ParameterID{"cutoff", 1}, "Cutoff",
      juce::NormalisableRange<float>(80.0f, 12000.0f, 0.5f, 0.25f), 8000.0f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      ParameterID{"resonance", 1}, "Resonance",
      juce::NormalisableRange<float>(0.1f, 1.2f), 0.7f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      ParameterID{"tone", 1}, "Tone",
      juce::NormalisableRange<float>(150.0f, 12000.0f, 0.6f), 4000.0f));
  for (int i = 0; i < numSteps; ++i) {
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        ParameterID{"step" + juce::String(i + 1), 1},
        "Step " + juce::String(i + 1),
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f));
  }
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      ParameterID{"attack", 1}, "Attack",
      juce::NormalisableRange<float>(1.0f, 500.0f), 40.0f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      ParameterID{"release", 1}, "Release",
      juce::NormalisableRange<float>(5.0f, 1000.0f), 200.0f));
  return {params.begin(), params.end()};
}

void MAStyleJuceDemoAudioProcessor::prepareToPlay(double sampleRate,
                                                  int samplesPerBlock) {
  juce::ignoreUnused(samplesPerBlock);
  juce::dsp::ProcessSpec spec{sampleRate, (juce::uint32)samplesPerBlock,
                              (juce::uint32)getTotalNumInputChannels()};
  dryWet.reset();
  dryWet.setMixingRule(juce::dsp::DryWetMixingRule::linear);
  dryWet.prepare(spec);
  rmsMeter.reset(sampleRate, 0.05);

  stepDeltaPerSample = (2.0 /* steps per second */ * (double)numSteps) / sampleRate;
  stepPhase = 0.0;
}

bool MAStyleJuceDemoAudioProcessor::isBusesLayoutSupported(
    const BusesLayout &layouts) const {
  return layouts.getMainInputChannelSet() == layouts.getMainOutputChannelSet();
}

void MAStyleJuceDemoAudioProcessor::processBlock(
    juce::AudioBuffer<float> &buffer, juce::MidiBuffer &midi) {
  juce::ignoreUnused(midi);
  juce::ScopedNoDenormals noDenormals;

  auto totalNumInputChannels = getTotalNumInputChannels();
  auto totalNumOutputChannels = getTotalNumOutputChannels();
  for (auto i = totalNumInputChannels; i < totalNumOutputChannels; ++i)
    buffer.clear(i, 0, buffer.getNumSamples());

  auto *drive = state.getRawParameterValue("drive");
  auto *mix = state.getRawParameterValue("mix");
  auto *tone = state.getRawParameterValue("tone");

  auto block = juce::dsp::AudioBlock<float>(buffer);
  dryWet.pushDrySamples(block);

  // Simple drive + dry/wet (placeholder DSP, kept lightweight).
  auto driveGain = juce::Decibels::decibelsToGain(drive->load());

  // Step modulation: pick current step based on block time.
  auto currentStepIndex = static_cast<size_t>(static_cast<int>(stepPhase) % numSteps);
  stepPhase += stepDeltaPerSample * buffer.getNumSamples();
  auto stepVal = stepParams[currentStepIndex] ? stepParams[currentStepIndex]->load() : 0.0f;
  auto stepGain = 1.0f + (0.5f * stepVal); // up to +6 dB-ish

  driveGain *= stepGain;
  buffer.applyGain(driveGain);

  // Lightweight tone tilt: one-pole LP per channel.
  auto toneHz = tone->load();
  auto alpha = 1.0f - std::exp(-2.0 * juce::MathConstants<double>::pi * (double)toneHz / getSampleRate());
  auto* left = buffer.getWritePointer(0);
  auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer(1) : nullptr;
  for (int i = 0; i < buffer.getNumSamples(); ++i)
  {
      toneStateL += (float)alpha * (left[i] - toneStateL);
      left[i] = toneStateL;
      if (right)
      {
          toneStateR += (float)alpha * (right[i] - toneStateR);
          right[i] = toneStateR;
      }
  }

  dryWet.setWetMixProportion(mix->load());
  dryWet.mixWetSamples(block);

  collector.push(buffer);

  // RMS meter
  auto numSamples = buffer.getNumSamples();
  float sumSquares = 0.0f;
  for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
    sumSquares += buffer.getRMSLevel(ch, 0, numSamples);
  auto avg = sumSquares / juce::jmax(1, buffer.getNumChannels());
  rmsMeter.setTargetValue(avg);
  lastRms = rmsMeter.getNextValue();
}

juce::AudioProcessorEditor *MAStyleJuceDemoAudioProcessor::createEditor() {
  return new MAStyleJuceDemoAudioProcessorEditor(*this);
}

void MAStyleJuceDemoAudioProcessor::getStateInformation(
    juce::MemoryBlock &destData) {
  auto stateTree = state.copyState();
  std::unique_ptr<juce::XmlElement> xml(stateTree.createXml());
  copyXmlToBinary(*xml, destData);
}

void MAStyleJuceDemoAudioProcessor::setStateInformation(const void *data,
                                                        int sizeInBytes) {
  std::unique_ptr<juce::XmlElement> xmlState(
      getXmlFromBinary(data, sizeInBytes));
  if (xmlState.get() != nullptr)
    if (xmlState->hasTagName(state.state.getType()))
      state.replaceState(juce::ValueTree::fromXml(*xmlState));
}

void MAStyleJuceDemoAudioProcessor::requestSidecar(const SidecarMeta &meta) {
  auto stats = collector.snapshotAndReset();
  writer.enqueue(stats, meta);
  // Do not let the pool delete our stack-owned job.
  pool.addJob(&writer, false);
}

juce::AudioProcessor *JUCE_CALLTYPE createPluginFilter() {
  return new MAStyleJuceDemoAudioProcessor();
}
