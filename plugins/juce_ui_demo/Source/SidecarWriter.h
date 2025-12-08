#pragma once

#include "FeatureCollector.h"
#include <juce_core/juce_core.h>
#include <juce_data_structures/juce_data_structures.h>

struct SidecarMeta {
  juce::String trackId;
  juce::String sessionId;
  juce::String host = "unknown";
  juce::String version = "juce_probe_features_v1";
};

class SidecarWriter : public juce::ThreadPoolJob {
public:
  SidecarWriter() : ThreadPoolJob("SidecarWriter") {}

  static juce::File defaultRoot() {
    auto home = juce::File::getSpecialLocation(juce::File::userHomeDirectory);
    return home.getChildFile("music-advisor/data/features_output/juce_probe");
  }

  void enqueue(const ProbeStats &stats, const SidecarMeta &meta) {
    juce::SpinLock::ScopedLockType lock(queueLock);
    pendingStats = stats;
    pendingMeta = meta;
    hasWork = true;
  }

  JobStatus runJob() override {
    if (!hasWork)
      return juce::ThreadPoolJob::jobHasFinished;
    ProbeStats statsCopy;
    SidecarMeta metaCopy;
    {
      juce::SpinLock::ScopedLockType lock(queueLock);
      statsCopy = pendingStats;
      metaCopy = pendingMeta;
      hasWork = false;
    }
    writeSidecar(statsCopy, metaCopy);
    return juce::ThreadPoolJob::jobHasFinished;
  }

private:
  void writeSidecar(const ProbeStats &stats, const SidecarMeta &meta) {
    juce::DynamicObject obj;
    obj.setProperty("version", meta.version);
    obj.setProperty("track_id", meta.trackId);
    obj.setProperty("session_id", meta.sessionId);
    obj.setProperty("host", meta.host);
    obj.setProperty("sample_rate", stats.sampleRate);

    juce::DynamicObject *feats = new juce::DynamicObject();
    feats->setProperty("rms", stats.rms);
    feats->setProperty("peak", stats.peak);
    feats->setProperty("crest", stats.crest);
    obj.setProperty("features", juce::var(feats));
    auto json = juce::JSON::toString(juce::var(&obj), true);

    auto root = defaultRoot();
    auto trackDir =
        root.getChildFile(meta.trackId.isEmpty() ? "untitled" : meta.trackId);
    auto timestamp = juce::Time::getCurrentTime().toString(true, true);
    auto outDir = trackDir.getChildFile(timestamp);
    outDir.createDirectory();
    auto outFile = outDir.getChildFile("juce_probe_features.json");
    outFile.replaceWithText(json);
  }

  juce::SpinLock queueLock;
  ProbeStats pendingStats;
  SidecarMeta pendingMeta;
  bool hasWork{false};
};
