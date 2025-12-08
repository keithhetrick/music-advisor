#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

struct ProbeStats {
  double rms = 0.0;
  double peak = 0.0;
  double crest = 0.0;
  int64_t samples = 0;
  double sampleRate = 44100.0;
};

/** Lightweight feature collector for RMS/peak/crest.
    All fields are atomic so the audio thread never locks. */
class FeatureCollector {
public:
  void prepare(double sr) {
    sampleRate.store(sr);
    reset();
  }

  void reset() {
    sumSquares.store(0.0);
    peak.store(0.0f);
    totalSamples.store(0);
  }

  void push(const juce::AudioBuffer<float> &buffer) {
    const int numSamples = buffer.getNumSamples();
    const int numChannels = buffer.getNumChannels();
    if (numSamples == 0 || numChannels == 0)
      return;

    float localPeak = 0.0f;
    double localSum = 0.0;
    for (int ch = 0; ch < numChannels; ++ch) {
      auto *data = buffer.getReadPointer(ch);
      for (int i = 0; i < numSamples; ++i) {
        const float s = data[i];
        localSum += static_cast<double>(s) * static_cast<double>(s);
        localPeak = std::max(localPeak, std::abs(s));
      }
    }
    peak.store(std::max(peak.load(), localPeak));
    sumSquares.store(sumSquares.load() + localSum);
    totalSamples.store(totalSamples.load() + static_cast<int64_t>(numSamples));
  }

  ProbeStats snapshotAndReset() {
    const double sum = sumSquares.exchange(0.0);
    const double pk = peak.exchange(0.0f);
    const int64_t n = totalSamples.exchange(0);
    ProbeStats stats;
    stats.samples = n;
    stats.sampleRate = sampleRate.load();
    if (n > 0) {
      const double rmsLin = std::sqrt(sum / static_cast<double>(n));
      stats.rms = rmsLin;
      stats.peak = pk;
      stats.crest = (rmsLin > 0.0) ? pk / rmsLin : 0.0;
    }
    return stats;
  }

private:
  std::atomic<double> sumSquares{0.0};
  std::atomic<float> peak{0.0f};
  std::atomic<int64_t> totalSamples{0};
  std::atomic<double> sampleRate{44100.0};
};
