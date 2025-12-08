#include "PluginProcessor.h"
#include "PluginEditor.h"

MAStyleJuceDemoAudioProcessor::MAStyleJuceDemoAudioProcessor()
    : AudioProcessor(
          BusesProperties()
              .withInput("Input", juce::AudioChannelSet::stereo(), true)
              .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      state(*this, nullptr, "MASTYLE_DEMO", createLayout()) {
  rmsMeter.reset(48000.0, 0.05);
}

MAStyleJuceDemoAudioProcessor::~MAStyleJuceDemoAudioProcessor() {
  pool.removeAllJobs(true, 1000);
}

juce::AudioProcessorValueTreeState::ParameterLayout
MAStyleJuceDemoAudioProcessor::createLayout() {
  std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      "drive", "Drive", juce::NormalisableRange<float>(0.0f, 24.0f), 6.0f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      "mix", "Mix", juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      "cutoff", "Cutoff",
      juce::NormalisableRange<float>(80.0f, 12000.0f, 0.5f, 0.25f), 8000.0f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      "resonance", "Resonance", juce::NormalisableRange<float>(0.1f, 1.2f),
      0.7f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      "attack", "Attack", juce::NormalisableRange<float>(1.0f, 500.0f), 40.0f));
  params.push_back(std::make_unique<juce::AudioParameterFloat>(
      "release", "Release", juce::NormalisableRange<float>(5.0f, 1000.0f),
      200.0f));
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

  auto block = juce::dsp::AudioBlock<float>(buffer);
  dryWet.pushDrySamples(block);

  // Simple drive + dry/wet (placeholder DSP, kept lightweight).
  auto driveGain = juce::Decibels::decibelsToGain(drive->load());
  buffer.applyGain(driveGain);

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
