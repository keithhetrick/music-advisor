#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

#include "dsp/FeatureCollector.h"

class MusicAdvisorProbeAudioProcessor : public juce::AudioProcessor
{
public:
    MusicAdvisorProbeAudioProcessor();
    ~MusicAdvisorProbeAudioProcessor() override = default;

    //==============================================================================
    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;

    bool isBusesLayoutSupported(const BusesLayout& layouts) const override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    //==============================================================================
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    //==============================================================================
    const juce::String getName() const override;

    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }

    //==============================================================================
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}

    //==============================================================================
    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    // UI/helpers
    juce::AudioProcessorValueTreeState& getValueTreeState() { return apvts; }
    void requestSnapshotFromUI(const juce::String& trackId,
                               const juce::String& sessionId,
                               const juce::String& dataRootOverride);
    juce::String getLastSnapshotPath() const;
    bool isWritingSnapshot() const;
    void setTrackId(const juce::String& trackId);
    void setSessionId(const juce::String& sessionId);
    juce::String getTrackId() const;
    juce::String getSessionId() const;
    juce::String getHostName() const;

private:
    juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();
    ProbeFrame makeFrame(const juce::AudioBuffer<float>& buffer, int numSamples) const;

    FeatureCollector collector;
    juce::AudioProcessorValueTreeState apvts;
    juce::ValueTree metaState{ "Meta" };

    double samplesProcessed{ 0.0 };
    juce::String hostName{"UnknownHost"};
    juce::String buildId{"dev"};

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MusicAdvisorProbeAudioProcessor)
};
