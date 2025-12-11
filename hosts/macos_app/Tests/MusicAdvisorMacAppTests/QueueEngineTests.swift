import XCTest
@testable import MAQueue

@MainActor
final class QueueEngineTests: XCTestCase {
    func testStartProcessesPendingAndIngestsOnSuccess() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = StubResolver()
        let persistence = QueuePersistence(url: tempQueueURL())
        let outbox = IngestOutbox(url: tempOutboxURL(), persist: false)
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: persistence,
                                 outbox: outbox)
        let job = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", preparedCommand: ["echo", "hi"], preparedOutPath: "/tmp/out.json")
        engine.enqueue([job])
        runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: ""))

        try await waitFor(timeout: 3.0) { engine.jobs.count == 1 }
        engine.start()

        try await waitFor(timeout: 6.0) {
            engine.jobs.first?.status == .done && sink.ingested.count == 1
        }

        XCTAssertEqual(engine.jobs.first?.status, Job.Status.done)
        XCTAssertEqual(sink.ingested.first?.path, job.fileURL.path)
    }

    func testFailureThenContinuesToNextPending() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = StubResolver()
        let persistence = QueuePersistence(url: tempQueueURL())
        let outbox = IngestOutbox(url: tempOutboxURL(), persist: false)
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: persistence,
                                 outbox: outbox)
        let first = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", preparedCommand: ["echo", "fail"])
        let second = Job(fileURL: URL(fileURLWithPath: "/tmp/b.wav"), displayName: "b", preparedCommand: ["echo", "ok"])
        engine.enqueue([first, second])
        runner.enqueueResult(.init(exitCode: 1, stdout: "", stderr: "err"))
        runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: ""))

        try await waitFor(timeout: 3.0) { engine.jobs.count == 2 }
        engine.start()

        try await waitFor(timeout: 6.0) {
            engine.jobs.contains(where: { $0.status == .failed }) &&
            engine.jobs.contains(where: { $0.status == .done })
        }
        try await waitFor(timeout: 6.0) {
            sink.ingested.count == 1
        }

        XCTAssertEqual(engine.jobs.map { $0.status }, [Job.Status.failed, Job.Status.done])
        XCTAssertEqual(sink.ingested.count, 1)
        XCTAssertEqual(sink.ingested.first?.path, second.fileURL.path)
    }

    func testStopCancelsCurrentAndPendingAndSkipsIngest() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = RecordingResolver()
        let persistence = QueuePersistence(url: tempQueueURL())
        let outbox = IngestOutbox(url: tempOutboxURL(), persist: false)
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: persistence,
                                 outbox: outbox)
        let job1 = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", preparedCommand: ["sleep", "1"], preparedOutPath: "/tmp/out1.json")
        let job2 = Job(fileURL: URL(fileURLWithPath: "/tmp/b.wav"), displayName: "b", preparedCommand: ["sleep", "1"], preparedOutPath: "/tmp/out2.json")
        engine.enqueue([job1, job2])
        runner.hold = true

        try await waitFor(timeout: 3.0) { engine.jobs.count == 2 }
        engine.start()
        try await waitFor(timeout: 3.0) { engine.jobs.first?.status == .running }
        engine.stop()
        runner.finish(with: .init(exitCode: 0, stdout: "", stderr: ""))

        try await waitFor(timeout: 12.0) {
            engine.jobs.allSatisfy { $0.status != .running && $0.status != .pending }
        }

        XCTAssertTrue(engine.jobs.allSatisfy { $0.status == .canceled || $0.status == .failed })
        try await waitFor(timeout: 4.0) { resolver.cleanupCalled }
        XCTAssertTrue(sink.ingested.isEmpty)
        XCTAssertTrue(resolver.cleanupCalled)
    }

    func testResumeCanceledMovesBackToPending() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = StubResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)
        let job = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", status: .canceled, preparedCommand: ["echo", "hi"])
        engine.enqueue([job])

        engine.resumeCanceled()

        XCTAssertEqual(engine.jobs.first?.status, Job.Status.pending)
    }

    func testResumeCanceledThenStartProcesses() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = RecordingResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)
        let job = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", status: .canceled, preparedCommand: ["echo", "hi"], preparedOutPath: "/tmp/out.json")
        engine.enqueue([job])
        runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: ""))

        engine.resumeCanceled()
        try await waitFor(timeout: 2.0) { engine.jobs.count == 1 }
        engine.start()

        try await waitFor(timeout: 6.0) {
            engine.jobs.first?.status == .done
        }

        XCTAssertEqual(engine.jobs.first?.status, .done)
        XCTAssertEqual(sink.ingested.count, 1)
        XCTAssertTrue(resolver.finalizedCalled)
        XCTAssertTrue(resolver.finalFileExists)
    }

    func testSpawnErrorMarksFailedAndSkipsIngest() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = RecordingResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)
        let job = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", preparedCommand: ["echo", "hi"])
        engine.enqueue([job])
        runner.enqueueResult(.init(exitCode: 127, stdout: "", stderr: "", spawnError: "boom"))

        try await waitFor(timeout: 3.0) { engine.jobs.count == 1 }
        engine.start()

        try await waitFor(timeout: 5.0) {
            engine.jobs.first?.status == .failed
        }

        XCTAssertEqual(engine.jobs.first?.status, Job.Status.failed)
        XCTAssertTrue(sink.ingested.isEmpty)
        XCTAssertFalse(resolver.finalizedCalled)
    }

    func testProcessesMultipleJobsSequentially() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = StubResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)
        let jobs = (0..<5).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/tmp/file\(idx).wav"),
                displayName: "file\(idx)",
                preparedCommand: ["echo", "\(idx)"],
                preparedOutPath: "/tmp/out\(idx).json")
        }
        engine.enqueue(jobs)
        jobs.forEach { _ in runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: "")) }

        try await waitFor(timeout: 4.0) { engine.jobs.count == jobs.count }
        engine.start()

        try await waitFor(timeout: 12.0) {
            engine.jobs.allSatisfy { $0.status == .done }
        }
        XCTAssertTrue(engine.jobs.allSatisfy { $0.status == .done })
    }

    func testIngestsExactlyOncePerSuccessfulJob() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = StubResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)
        let success = Job(fileURL: URL(fileURLWithPath: "/tmp/s.wav"), displayName: "s", preparedCommand: ["echo", "hi"])
        let failure = Job(fileURL: URL(fileURLWithPath: "/tmp/f.wav"), displayName: "f", preparedCommand: ["false"])
        engine.enqueue([success, failure])
        runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: ""))
        runner.enqueueResult(.init(exitCode: 1, stdout: "", stderr: "boom"))

        try await waitFor(timeout: 2.0) { engine.jobs.count == 2 }
        engine.start()

        try await waitFor(timeout: 7.0) {
            engine.jobs.contains(where: { $0.status == .done }) &&
            engine.jobs.contains(where: { $0.status == .failed })
        }
        XCTAssertEqual(sink.ingested.count, 1)
        XCTAssertEqual(sink.ingested.first?.path, success.fileURL.path)
    }

    func testDoesNotReenqueueAlreadyDoneJob() async throws {
        let runner = ControlledRunner()
        let sink = RecordingSink()
        let resolver = StubResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)
        let job = Job(fileURL: URL(fileURLWithPath: "/tmp/once.wav"), displayName: "once", preparedCommand: ["echo", "hi"])
        engine.enqueue([job])
        runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: ""))

        try await waitFor(timeout: 2.0) { engine.jobs.count == 1 }
        engine.start()
        try await waitFor(timeout: 6.0) { engine.jobs.first?.status == .done }
        XCTAssertEqual(sink.ingested.count, 1)

        // Restart should not enqueue ingest again for the same completed job.
        engine.start()
        try await waitFor(timeout: 2.0) { sink.ingested.count == 1 }
    }

    func testEnqueueAfterStopRequiresExplicitRestart() async throws {
        let runner = ControlledRunner()
        runner.hold = true
        let sink = RecordingSink()
        let resolver = StubResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)
        let initial = Job(fileURL: URL(fileURLWithPath: "/tmp/run.wav"), displayName: "run", preparedCommand: ["echo", "run"])
        engine.enqueue([initial])
        try await waitFor(timeout: 2.0) { engine.jobs.count == 1 }
        engine.start()
        try await waitFor(timeout: 2.0) { engine.jobs.first?.status == .running }
        engine.stop()

        let next = Job(fileURL: URL(fileURLWithPath: "/tmp/new.wav"), displayName: "new", preparedCommand: ["echo", "new"])
        engine.enqueue([next])
        XCTAssertEqual(engine.jobs.last?.status, .pending)

        // Finish stopped run and ensure new job does not auto-start.
        runner.finish(with: .init(exitCode: 0, stdout: "", stderr: ""))
        try await waitFor(timeout: 3.0) { engine.jobs.last?.status == .pending }

        runner.hold = false
        runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: ""))
        engine.start()
        try await waitFor(timeout: 15.0) { engine.jobs.last?.status == .done }
    }
}
