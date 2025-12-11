import XCTest
@testable import MAQueue

final class IngestProcessorTests: XCTestCase {
    func testProcessorRetriesAndThenSucceeds() async throws {
        let clock = ManualClock()
        let outbox = IngestOutbox(url: tempOutboxURLForIngest(), dateProvider: { clock.now })
        let sink = FlakySink(failuresBeforeSuccess: 1)
        let processor = IngestProcessor(outbox: outbox, sink: sink, onMetrics: nil)
        let file = URL(fileURLWithPath: "/tmp/retry.wav")
        await outbox.enqueue(fileURL: file, jobID: UUID())

        processor.kick()
        // Wait for first attempt to register and processor to finish cycle.
        try await waitForAsync(timeout: 1.0) {
            let snap = await outbox.snapshot()
            return sink.attempts >= 1 &&
            snap.errors == 1 &&
            snap.pending == 1
        }
        // First attempt fails; advance clock beyond backoff and kick again.
        clock.advance(seconds: 3)
        processor.kick()

        try await waitForAsync(timeout: 1.0) {
            let snap = await outbox.snapshot()
            return sink.succeeded && snap.pending == 0
        }
        let snapshot = await outbox.snapshot()
        XCTAssertEqual(snapshot.pending, 0)
        XCTAssertEqual(snapshot.errors, 0)
        XCTAssertGreaterThanOrEqual(sink.attempts, 2)
    }

    func testMetricsHookFiresOncePerBatch() async throws {
        let outbox = IngestOutbox(url: tempOutboxURLForIngest(), persist: false)
        let sink = FlakySink(failuresBeforeSuccess: 0)
        var metricsCount = 0
        let processor = IngestProcessor(outbox: outbox, sink: sink) {
            metricsCount += 1
        }

        await outbox.enqueue(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), jobID: UUID())
        await outbox.enqueue(fileURL: URL(fileURLWithPath: "/tmp/b.wav"), jobID: UUID())
        processor.kick()

        try await waitForAsync(timeout: 1.0) { metricsCount == 1 }
        let snapshot = await outbox.snapshot()
        XCTAssertEqual(snapshot.pending, 0)
        XCTAssertEqual(metricsCount, 1)
    }
}

private final class FlakySink: IngestSink {
    let failuresBeforeSuccess: Int
    private(set) var attempts = 0
    private(set) var succeeded = false

    init(failuresBeforeSuccess: Int) {
        self.failuresBeforeSuccess = failuresBeforeSuccess
    }

    func ingest(fileURL: URL, jobID: UUID?) async -> Bool {
        attempts += 1
        if attempts <= failuresBeforeSuccess {
            return false
        }
        succeeded = true
        return true
    }
}

private func tempOutboxURLForIngest() -> URL {
    FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("outbox.json")
}

private final class ManualClock {
    private(set) var now: Date

    init(now: Date = Date()) {
        self.now = now
    }

    func advance(seconds: TimeInterval) {
        now = now.addingTimeInterval(seconds)
    }
}

private func waitForAsync(timeout: TimeInterval = 1.0, condition: @escaping () async -> Bool) async throws {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        if await condition() { return }
        try await Task.sleep(nanoseconds: 20_000_000)
    }
    XCTFail("Condition not met within \(timeout) seconds")
}
