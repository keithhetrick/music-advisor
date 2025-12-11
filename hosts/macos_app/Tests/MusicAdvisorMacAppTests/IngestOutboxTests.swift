import XCTest
@testable import MAQueue

final class IngestOutboxTests: XCTestCase {
    func testEnqueueDeduplicatesByPath() async {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let outbox = IngestOutbox(url: url)
        let file = URL(fileURLWithPath: "/tmp/file.wav")

        await outbox.enqueue(fileURL: file, jobID: nil)
        await outbox.enqueue(fileURL: file, jobID: nil)

        let snapshot = await outbox.snapshot()
        XCTAssertEqual(snapshot.pending, 1)
    }

    func testMarkFailureTracksErrors() async {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let outbox = IngestOutbox(url: url)
        let file = URL(fileURLWithPath: "/tmp/file.wav")
        await outbox.enqueue(fileURL: file, jobID: nil)
        guard let entry = await outbox.nextPending() else {
            return XCTFail("expected pending entry")
        }

        await outbox.markFailure(id: entry.id, error: "boom")
        let snapshot = await outbox.snapshot()

        XCTAssertEqual(snapshot.pending, 1)
        XCTAssertEqual(snapshot.errors, 1)
    }

    func testMarkSuccessRemovesEntry() async {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let outbox = IngestOutbox(url: url)
        let file = URL(fileURLWithPath: "/tmp/file.wav")
        await outbox.enqueue(fileURL: file, jobID: nil)
        guard let entry = await outbox.nextPending() else {
            return XCTFail("expected pending entry")
        }

        await outbox.markSuccess(id: entry.id)
        let snapshot = await outbox.snapshot()

        XCTAssertEqual(snapshot.pending, 0)
        XCTAssertEqual(snapshot.errors, 0)
    }

    func testNextPendingRespectsBackoffDelay() async throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let outbox = IngestOutbox(url: url)
        let file = URL(fileURLWithPath: "/tmp/file.wav")
        await outbox.enqueue(fileURL: file, jobID: nil)
        guard let entry = await outbox.nextPending() else {
            return XCTFail("expected pending entry")
        }

        await outbox.markFailure(id: entry.id, error: "boom")
        let immediate = await outbox.nextPending()
        XCTAssertNil(immediate, "should respect delay after failure")

        try await Task.sleep(nanoseconds: 2_200_000_000)
        let afterDelay = await outbox.nextPending()
        XCTAssertNotNil(afterDelay, "should return entry after backoff window")
    }

    func testNextPendingStopsAfterMaxAttempts() async {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let outbox = IngestOutbox(url: url)
        let file = URL(fileURLWithPath: "/tmp/file.wav")
        await outbox.enqueue(fileURL: file, jobID: nil)
        guard let entry = await outbox.nextPending() else {
            return XCTFail("expected pending entry")
        }
        for _ in 0..<5 {
            await outbox.markFailure(id: entry.id, error: "boom")
        }

        let pending = await outbox.nextPending()
        XCTAssertNil(pending)
    }

    func testBackoffWithManualClock() async {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let clock = ManualClock()
        let outbox = IngestOutbox(url: url, dateProvider: { clock.now })
        let file = URL(fileURLWithPath: "/tmp/file.wav")
        await outbox.enqueue(fileURL: file, jobID: nil)
        guard let entry = await outbox.nextPending() else {
            return XCTFail("expected pending entry")
        }

        await outbox.markFailure(id: entry.id, error: "boom")
        let immediate = await outbox.nextPending()
        XCTAssertNil(immediate)

        clock.advance(seconds: 3)
        let afterDelay = await outbox.nextPending()
        XCTAssertNotNil(afterDelay)
    }
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
