#include "PluginProcessor.h"
#include "PluginEditor.h"

#include <JuceHeader.h>

MusicAdvisorProbeAudioProcessor::MusicAdvisorProbeAudioProcessor()
    : juce::AudioProcessor(BusesProperties()
                               .withInput("Input", juce::AudioChannelSet::stereo(), true)
                               .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      apvts(*this, nullptr, "PARAMS", createParameterLayout())
{
    metaState.setProperty("trackId", "untitled", nullptr);
    metaState.setProperty("sessionId", "session", nullptr);

    juce::PluginHostType hostType;
    hostName = hostType.getHostDescription();
   #if defined(JucePlugin_VersionString)
    buildId = JucePlugin_VersionString;
   #endif
}

const juce::String MusicAdvisorProbeAudioProcessor::getName() const
{
    return JucePlugin_Name;
}

void MusicAdvisorProbeAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    juce::ignoreUnused(samplesPerBlock);
    samplesProcessed = 0.0;
    collector.prepare(sampleRate, samplesPerBlock);
}

void MusicAdvisorProbeAudioProcessor::releaseResources()
{
    collector.reset();
}

bool MusicAdvisorProbeAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto mainInLayout = layouts.getChannelSet(true, 0);
    const auto mainOutLayout = layouts.getChannelSet(false, 0);
    if (mainInLayout != mainOutLayout)
        return false;

    return (mainInLayout == juce::AudioChannelSet::mono() || mainInLayout == juce::AudioChannelSet::stereo());
}

void MusicAdvisorProbeAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                                   juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    const auto totalNumInputChannels = getTotalNumInputChannels();
    const auto totalNumOutputChannels = getTotalNumOutputChannels();
    for (int i = totalNumInputChannels; i < totalNumOutputChannels; ++i)
        buffer.clear(i, 0, buffer.getNumSamples());

    const bool captureEnabled = apvts.getRawParameterValue("capture_enabled")->load() >= 0.5f;
    const auto numSamples = buffer.getNumSamples();
    if (captureEnabled && buffer.getNumChannels() > 0 && numSamples > 0)
    {
        auto frame = makeFrame(buffer, numSamples);
        collector.pushFrame(frame);
    }

    samplesProcessed += numSamples;
}

ProbeFrame MusicAdvisorProbeAudioProcessor::makeFrame(const juce::AudioBuffer<float>& buffer,
                                                      int numSamples) const
{
    const int numChannels = buffer.getNumChannels();
    double sumSquares = 0.0;
    float peakLinear = 0.0f;

    for (int ch = 0; ch < numChannels; ++ch)
    {
        const auto* channelData = buffer.getReadPointer(ch);
        for (int i = 0; i < numSamples; ++i)
        {
            const float sample = channelData[i];
            sumSquares += (double) sample * (double) sample;
            peakLinear = std::max(peakLinear, std::abs(sample));
        }
    }

    ProbeFrame frame;
    frame.sampleCount = numSamples * numChannels;
    frame.sumSquares = sumSquares;
    frame.peakLinear = peakLinear;
    frame.timestampSec = samplesProcessed / std::max(1.0, getSampleRate());
    return frame;
}

bool MusicAdvisorProbeAudioProcessor::hasEditor() const
{
    return true;
}

juce::AudioProcessorEditor* MusicAdvisorProbeAudioProcessor::createEditor()
{
    return new MusicAdvisorProbeAudioProcessorEditor(*this);
}

void MusicAdvisorProbeAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    juce::MemoryOutputStream stream(destData, false);
    juce::ValueTree state("MAProbeState");
    state.setProperty("trackId", getTrackId(), nullptr);
    state.setProperty("sessionId", getSessionId(), nullptr);
    state.addChild(apvts.copyState(), -1, nullptr);
    state.writeToStream(stream);
}

void MusicAdvisorProbeAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    auto state = juce::ValueTree::readFromData(data, (size_t) sizeInBytes);
    if (! state.isValid())
        return;

    if (auto params = state.getChildWithName("PARAMS"); params.isValid())
        apvts.replaceState(params);

    if (auto track = state.getProperty("trackId"); track.isString())
        setTrackId(track.toString());
    if (auto session = state.getProperty("sessionId"); session.isString())
        setSessionId(session.toString());
}

juce::AudioProcessorValueTreeState::ParameterLayout MusicAdvisorProbeAudioProcessor::createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
    params.push_back(std::make_unique<juce::AudioParameterBool>("capture_enabled",
                                                                "Capture Enabled",
                                                                true));
    return { params.begin(), params.end() };
}

void MusicAdvisorProbeAudioProcessor::requestSnapshotFromUI(const juce::String& trackId,
                                                            const juce::String& sessionId,
                                                            const juce::String& dataRootOverride)
{
    setTrackId(trackId);
    setSessionId(sessionId);

    SnapshotRequest req;
    req.trackId = getTrackId();
    req.sessionId = getSessionId();
    req.dataRootOverride = dataRootOverride;
    req.hostName = getHostName();
    req.sampleRate = getSampleRate();
    req.buildId = buildId;
    collector.requestSnapshot(req);
}

juce::String MusicAdvisorProbeAudioProcessor::getLastSnapshotPath() const
{
    return collector.getLastWritePath();
}

bool MusicAdvisorProbeAudioProcessor::isWritingSnapshot() const
{
    return collector.isWritingSnapshot();
}

void MusicAdvisorProbeAudioProcessor::setTrackId(const juce::String& trackId)
{
    metaState.setProperty("trackId", trackId, nullptr);
}

void MusicAdvisorProbeAudioProcessor::setSessionId(const juce::String& sessionId)
{
    metaState.setProperty("sessionId", sessionId, nullptr);
}

juce::String MusicAdvisorProbeAudioProcessor::getTrackId() const
{
    return metaState.getProperty("trackId").toString();
}

juce::String MusicAdvisorProbeAudioProcessor::getSessionId() const
{
    return metaState.getProperty("sessionId").toString();
}

juce::String MusicAdvisorProbeAudioProcessor::getHostName() const
{
    return hostName;
}
