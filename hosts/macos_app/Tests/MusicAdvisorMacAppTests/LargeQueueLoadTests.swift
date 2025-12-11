import XCTest
@testable import MAQueue

@MainActor
final class LargeQueueLoadTests: XCTestCase {
    func testStopCancelsRemainingOnLargeQueue() async throws {
        let runner = ImmediateRunner(hold: true)
        let sink = RecordingSink()
        let resolver = StubResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)

        let jobs = (0..<100).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/tmp/file\(idx).wav"),
                displayName: "file\(idx)",
                preparedCommand: ["echo", "\(idx)"],
                preparedOutPath: "/tmp/out\(idx).json")
        }
        engine.enqueue(jobs)

        engine.start()
        try await waitFor(timeout: 1.0) { engine.jobs.first?.status == .running }
        engine.stop()
        runner.releaseHold(result: .init(exitCode: 0, stdout: "", stderr: ""))

        try await waitFor(timeout: 3.0) {
            engine.jobs.allSatisfy { $0.status == .canceled }
        }

        XCTAssertEqual(engine.jobs.filter { $0.status == .canceled }.count, 100)
        XCTAssertTrue(sink.ingested.isEmpty)
    }

    func testConcurrentEnqueueAndStopDoesNotCrash() async throws {
        let runner = ImmediateRunner()
        let sink = RecordingSink()
        let resolver = StubResolver()
        let engine = QueueEngine(runner: runner,
                                 ingestor: sink,
                                 resolver: resolver,
                                 persistence: QueuePersistence(url: tempQueueURL()),
                                 outbox: IngestOutbox(url: tempOutboxURL(), persist: false),
                                 metricsHook: nil)

        let initialJobs = (0..<20).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/tmp/file\(idx).wav"),
                displayName: "file\(idx)",
                preparedCommand: ["echo", "\(idx)"],
                preparedOutPath: "/tmp/out\(idx).json")
        }
        engine.enqueue(initialJobs)
        runner.queuedResult = .init(exitCode: 0, stdout: "", stderr: "")

        await withTaskGroup(of: Void.self) { group in
            group.addTask {
                await engine.start()
            }
            group.addTask {
                for i in 20..<40 {
                    let job = Job(fileURL: URL(fileURLWithPath: "/tmp/file\(i).wav"),
                                  displayName: "file\(i)",
                                  preparedCommand: ["echo", "\(i)"],
                                  preparedOutPath: "/tmp/out\(i).json")
                    await engine.enqueue([job])
                    try? await Task.sleep(nanoseconds: 10_000_000) // slight stagger
                }
            }
            group.addTask {
                try? await Task.sleep(nanoseconds: 200_000_000)
                await engine.stop()
            }
        }

        try await waitFor(timeout: 5.0) {
            engine.jobs.allSatisfy { $0.status != .running }
        }
    }
}

// MARK: - Helpers

private final class ImmediateRunner: QueueRunner {
    private let hold: Bool
    private var continuation: CheckedContinuation<QueueRunResult, Never>?
    var queuedResult: QueueRunResult?

    init(hold: Bool = false) {
        self.hold = hold
    }

    func run(job: Job) async -> QueueRunResult {
        if hold {
            return await withCheckedContinuation { cont in
                continuation = cont
            }
        }
        return queuedResult ?? QueueRunResult(exitCode: 0, stdout: "", stderr: "")
    }

    func releaseHold(result: QueueRunResult) {
        queuedResult = result
        continuation?.resume(returning: result)
        continuation = nil
    }
}

// RecordingSink, StubResolver, tempQueueURL/tempOutboxURL, and waitFor are provided by TestSupport.swift
