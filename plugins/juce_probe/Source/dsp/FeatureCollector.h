#pragma once

#include <juce_core/juce_core.h>
#include <juce_data_structures/juce_data_structures.h>

// One analysis frame pushed from the audio thread.
struct ProbeFrame
{
    double timestampSec{};
    double sumSquares{};
    int sampleCount{};
    float peakLinear{};
};

struct TimelinePoint
{
    double timeSec{};
    float rmsDb{};
    float peakDb{};
};

struct SnapshotRequest
{
    juce::String trackId{"untitled"};
    juce::String sessionId{"session"};
    juce::String hostName{"UnknownHost"};
    juce::String dataRootOverride{}; // optional MA_DATA_ROOT override from UI/env
    juce::String buildId{"dev"};
    double sampleRate{};
};

// Drains RT frames, aggregates loudness/peaks, and writes JSON snapshots on demand.
class FeatureCollector : private juce::Thread
{
public:
    FeatureCollector();
    ~FeatureCollector() override;

    void prepare(double sampleRate, int maxBlockSize);
    void reset();

    // Audio thread safe: lock-free push, drops frame if FIFO is saturated.
    void pushFrame(const ProbeFrame& frame);

    // UI thread: request a JSON snapshot at the next drain.
    void requestSnapshot(const SnapshotRequest& request);

    // Non-RT query helpers.
    juce::String getLastWritePath() const;
    bool isWritingSnapshot() const;

private:
    void run() override;
    void drainFrames();
    void writeSnapshotIfRequested();
    bool writeSnapshot(const SnapshotRequest& request);

    struct Aggregator
    {
        void reset();
        void ingest(const ProbeFrame& frame);
        double sampleRate{48000.0};
        double totalSeconds{0.0};
        double sumSquares{0.0};
        int64_t totalSamples{0};
        float maxPeak{0.0f};
        double lastTimelineWrite{-1.0};
        std::vector<TimelinePoint> timeline;
    };

    Aggregator aggregator;
    juce::AbstractFifo fifo;
    std::vector<ProbeFrame> fifoBuffer;
    std::atomic<bool> snapshotRequested{false};
    std::atomic<bool> writingSnapshot{false};
    SnapshotRequest pendingSnapshot;
    mutable std::mutex requestMutex;
    juce::String lastWritePath;
    int fifoCapacity{8192};
};
