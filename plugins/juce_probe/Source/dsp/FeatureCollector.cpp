#include "FeatureCollector.h"

#include <juce_audio_processors/juce_audio_processors.h>
#include <cstdlib>

namespace
{
constexpr double kTimelineSpacingSec = 0.25; // downsampled envelope for the sidecar
constexpr double kEpsilon = 1.0e-9;

juce::String sanitiseId(const juce::String& raw)
{
    auto cleaned = raw.trim();
    if (cleaned.isEmpty())
        cleaned = "untitled";
    return juce::File::createLegalFileName(cleaned);
}

juce::File defaultDataRoot()
{
    auto* env = std::getenv("MA_DATA_ROOT");
    if (env != nullptr && *env != '\0')
        return juce::File(juce::String(env)).getAbsoluteFile();

    auto home = juce::File::getSpecialLocation(juce::File::userHomeDirectory);
    return home.getChildFile("music-advisor").getChildFile("data");
}

juce::File resolveDataRoot(const SnapshotRequest& req)
{
    if (req.dataRootOverride.isNotEmpty())
        return juce::File(req.dataRootOverride).getAbsoluteFile();
    return defaultDataRoot();
}
} // namespace

FeatureCollector::FeatureCollector()
    : juce::Thread("FeatureCollectorWriter"), fifo(fifoCapacity)
{
    fifoBuffer.resize((size_t) fifoCapacity);
    aggregator.reset();
    startThread();
}

FeatureCollector::~FeatureCollector()
{
    stopThread(2000);
}

void FeatureCollector::prepare(double sampleRate, int maxBlockSize)
{
    juce::ignoreUnused(maxBlockSize);
    aggregator.sampleRate = sampleRate;
    aggregator.reset();
    fifo.reset();
}

void FeatureCollector::reset()
{
    aggregator.reset();
    fifo.reset();
    lastWritePath.clear();
}

void FeatureCollector::pushFrame(const ProbeFrame& frame)
{
    int start1, size1, start2, size2;
    fifo.prepareToWrite(1, start1, size1, start2, size2);
    if (size1 > 0)
    {
        fifoBuffer[(size_t) start1] = frame;
        fifo.finishedWrite(size1);
    }
    juce::ignoreUnused(start2, size2); // Single-region writes only.
}

void FeatureCollector::requestSnapshot(const SnapshotRequest& request)
{
    {
        const std::lock_guard<std::mutex> lock(requestMutex);
        pendingSnapshot = request;
    }
    snapshotRequested.store(true);
    notify();
}

juce::String FeatureCollector::getLastWritePath() const
{
    return lastWritePath;
}

bool FeatureCollector::isWritingSnapshot() const
{
    return writingSnapshot.load();
}

void FeatureCollector::Aggregator::reset()
{
    totalSeconds = 0.0;
    sumSquares = 0.0;
    totalSamples = 0;
    maxPeak = 0.0f;
    lastTimelineWrite = -1.0;
    timeline.clear();
}

void FeatureCollector::Aggregator::ingest(const ProbeFrame& frame)
{
    const double blockDuration = frame.sampleCount > 0 && sampleRate > 0.0
                                     ? (double) frame.sampleCount / sampleRate
                                     : 0.0;
    totalSeconds = std::max(totalSeconds, frame.timestampSec + blockDuration);
    sumSquares += frame.sumSquares;
    totalSamples += frame.sampleCount;
    maxPeak = std::max(maxPeak, frame.peakLinear);

    const bool first = lastTimelineWrite < 0.0;
    const bool spacedOut = (frame.timestampSec - lastTimelineWrite) >= kTimelineSpacingSec;
    if (first || spacedOut)
    {
        lastTimelineWrite = frame.timestampSec;
        const auto rmsLinear = std::sqrt(frame.sumSquares / std::max(1, frame.sampleCount));
        TimelinePoint point;
        point.timeSec = frame.timestampSec;
        point.rmsDb = (float) juce::Decibels::gainToDecibels(rmsLinear + kEpsilon);
        point.peakDb = (float) juce::Decibels::gainToDecibels(frame.peakLinear + kEpsilon);
        timeline.push_back(point);
    }
}

void FeatureCollector::run()
{
    while (! threadShouldExit())
    {
        drainFrames();
        writeSnapshotIfRequested();
        wait(25);
    }
}

void FeatureCollector::drainFrames()
{
    while (fifo.getNumReady() > 0)
    {
        int start1, size1, start2, size2;
        fifo.prepareToRead(1, start1, size1, start2, size2);
        if (size1 > 0)
            aggregator.ingest(fifoBuffer[(size_t) start1]);
        fifo.finishedRead(size1);
        juce::ignoreUnused(start2, size2);
    }
}

void FeatureCollector::writeSnapshotIfRequested()
{
    if (! snapshotRequested.load())
        return;

    SnapshotRequest requestCopy;
    {
        const std::lock_guard<std::mutex> lock(requestMutex);
        requestCopy = pendingSnapshot;
    }

    snapshotRequested.store(false);
    writingSnapshot.store(true);
    writeSnapshot(requestCopy);
    writingSnapshot.store(false);
}

bool FeatureCollector::writeSnapshot(const SnapshotRequest& request)
{
    if (aggregator.totalSamples <= 0)
        return false;

    const auto dataRoot = resolveDataRoot(request);
    const auto featuresRoot = dataRoot.getChildFile("features_output");
    const auto probeRoot = featuresRoot.getChildFile("juce_probe");
    const auto trackFolder = probeRoot.getChildFile(sanitiseId(request.trackId));

    const auto timestamp = juce::Time::getCurrentTime().formatted("%Y%m%d_%H%M%S");
    const auto snapshotFolder = trackFolder.getChildFile(timestamp);
    if (! snapshotFolder.createDirectory())
        return false;

    const auto outputFile = snapshotFolder.getChildFile("juce_probe_features.json");

    const double integratedRmsLinear = std::sqrt(aggregator.sumSquares / (double) std::max<int64_t>(1, aggregator.totalSamples));
    const double integratedRmsDb = juce::Decibels::gainToDecibels(integratedRmsLinear + kEpsilon);
    const double peakDb = juce::Decibels::gainToDecibels((double) aggregator.maxPeak + kEpsilon);
    const double crestDb = peakDb - integratedRmsDb;

    juce::DynamicObject::Ptr root = new juce::DynamicObject();
    root->setProperty("version", "juce_probe_features_v1");
    root->setProperty("track_id", request.trackId);
    root->setProperty("session_id", request.sessionId);
    root->setProperty("host", request.hostName);
    root->setProperty("sample_rate", request.sampleRate);
    root->setProperty("generated_at", juce::Time::getCurrentTime().toISO8601(true));
    root->setProperty("build", request.buildId);

    juce::DynamicObject::Ptr features = new juce::DynamicObject();
    juce::DynamicObject::Ptr global = new juce::DynamicObject();
    global->setProperty("duration_sec", aggregator.totalSeconds);
    global->setProperty("integrated_rms_db", integratedRmsDb);
    global->setProperty("peak_db", peakDb);
    global->setProperty("crest_factor_db", crestDb);
    features->setProperty("global", juce::var(global.get()));

    juce::Array<juce::var> timelineArray;
    timelineArray.ensureStorageFree((int) aggregator.timeline.size());
    for (const auto& point : aggregator.timeline)
    {
        juce::DynamicObject::Ptr obj = new juce::DynamicObject();
        obj->setProperty("time_sec", point.timeSec);
        obj->setProperty("rms_db", point.rmsDb);
        obj->setProperty("peak_db", point.peakDb);
        timelineArray.add(juce::var(obj.get()));
    }
    features->setProperty("timeline", juce::var(timelineArray));
    root->setProperty("features", juce::var(features.get()));

    juce::MemoryOutputStream jsonStream;
    jsonStream << juce::JSON::toString(juce::var(root.get()), true);

    juce::FileOutputStream out(outputFile);
    if (! out.openedOk())
        return false;

    out.setPosition(0);
    out.truncate();
    out.writeText(jsonStream.toString(), false, false, "\n");
    out.flush();

    lastWritePath = outputFile.getFullPathName();
    return true;
}
