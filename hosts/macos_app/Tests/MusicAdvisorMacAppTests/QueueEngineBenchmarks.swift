#if canImport(XCTest)
import XCTest
@testable import MAQueue

@MainActor
final class QueueEngineBenchmarks: XCTestCase {
    /// Optional micro-benchmark; skipped unless RUN_QUEUE_BENCH=1 to avoid slowing normal CI.
    func testStartProcessesHundredsQuickly() throws {
        guard ProcessInfo.processInfo.environment["RUN_QUEUE_BENCH"] == "1" else {
            throw XCTSkip("Set RUN_QUEUE_BENCH=1 to run queue benchmarks")
        }
        let runner = ControlledRunner()
        let engine = QueueEngine(
            runner: runner,
            ingestor: RecordingSink(),
            resolver: StubResolver(),
            persistence: QueuePersistence(url: tempQueueURL()),
            outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
            metricsHook: nil
        )
        let jobs = (0..<200).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/dev/null/\(idx).wav"),
                displayName: "bench-\(idx)",
                preparedCommand: ["echo", "\(idx)"],
                preparedOutPath: "/dev/null/\(idx).json")
        }
        engine.enqueue(jobs)
        jobs.forEach { _ in runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: "")) }

        measure {
            Task { @MainActor in engine.start() }
        }
    }
}
#endif
