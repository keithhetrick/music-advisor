import XCTest
@testable import MAQueue

@MainActor
final class LargeQueuePerformanceTests: XCTestCase {
    func testLargeQueueProcessesWithinBudget() async throws {
        let runner = ControlledRunner()
        let engine = makeEngine(runner: runner)
        let count = 100
        let jobs = (0..<count).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/tmp/perf\(idx).wav"),
                displayName: "perf\(idx)",
                preparedCommand: ["echo", "\(idx)"],
                preparedOutPath: "/tmp/perf\(idx).json")
        }
        engine.enqueue(jobs)
        jobs.forEach { _ in runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: "")) }

        try await waitFor(timeout: 4.0) { engine.jobs.count == count }
        engine.start()
        // Allow extra headroom on slower machines to reduce flake risk.
        try await waitFor(timeout: 20.0) { engine.jobs.allSatisfy { $0.status == .done } }
        XCTAssertEqual(engine.jobs.count, count)
    }

    // MARK: - Helpers

    private func makeEngine(runner: ControlledRunner) -> QueueEngine {
        let sink = RecordingSink()
        let resolver = StubResolver()
        let persistence = QueuePersistence(url: tempQueueURL())
        let outbox = IngestOutbox(url: tempOutboxURL(), persist: false)
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: persistence,
                                 outbox: outbox,
                                 metricsHook: nil)
        return engine
    }
}
