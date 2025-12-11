import XCTest
@testable import MAQueue

@MainActor
final class QueueEngineEdgeCaseTests: XCTestCase {
    func testStartOnEmptyQueueDoesNothing() {
        let (engine, _) = makeEngine()
        engine.start()
        XCTAssertTrue(engine.jobs.isEmpty)
    }

    func testResumeCanceledOnEmptyQueueDoesNothing() {
        let (engine, _) = makeEngine()
        engine.resumeCanceled()
        XCTAssertTrue(engine.jobs.isEmpty)
    }

    func testStopOnEmptyQueueDoesNothing() {
        let (engine, _) = makeEngine()
        engine.stop()
        XCTAssertTrue(engine.jobs.isEmpty)
    }

    func testAllCanceledThenClearAll() async throws {
        let (engine, _) = makeEngine()
        let jobs = (0..<3).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/tmp/c\(idx).wav"),
                displayName: "c\(idx)",
                status: .canceled,
                preparedCommand: ["echo", "hi"])
        }
        engine.enqueue(jobs)

        try await waitFor(timeout: 0.5) { engine.jobs.count == jobs.count }
        engine.clearAll()
        XCTAssertTrue(engine.jobs.isEmpty)
    }

    func testLargeBatchProcessesAll() async throws {
        let (engine, runner) = makeEngine()
        let count = 50
        let jobs = (0..<count).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/tmp/large\(idx).wav"),
                displayName: "large\(idx)",
                preparedCommand: ["echo", "\(idx)"],
                preparedOutPath: "/tmp/out\(idx).json")
        }
        engine.enqueue(jobs)
        jobs.forEach { _ in runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: "")) }

        try await waitFor(timeout: 8.0) { engine.jobs.count == count }
        engine.start()

        try await waitFor(timeout: 30.0) { engine.jobs.allSatisfy { $0.status == .done } }
        XCTAssertEqual(engine.jobs.count, count)
    }

    // MARK: - Helpers

    private func makeEngine() -> (QueueEngine, ControlledRunner) {
        let runner = ControlledRunner()
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
        return (engine, runner)
    }
}
