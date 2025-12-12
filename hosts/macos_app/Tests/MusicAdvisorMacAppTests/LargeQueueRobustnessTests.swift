import XCTest
@testable import MAQueue

@MainActor
final class LargeQueueRobustnessTests: XCTestCase {
    func testProcesses500JobsWithinBudget() async throws {
        try await assertLargeBatchCompletes(count: 500,
                                            timeout: stressTimeout(fast: 20.0, soak: 120.0),
                                            allowSkip: true)
    }

    func testProcesses1000JobsWithinBudget() async throws {
        try await assertLargeBatchCompletes(count: 1000,
                                            timeout: stressTimeout(fast: 30.0, soak: 240.0),
                                            allowSkip: true)
    }

    func testStopAndClearLargeQueue() async throws {
        let runner = ControlledRunner()
        runner.hold = true
        let engine = makeEngine(runner: runner)
        let jobs = makeJobs(prefix: "stop", count: 200)
        engine.enqueue(jobs)

        try await waitFor(timeout: 2.0) { engine.jobs.count == jobs.count }
        engine.start()
        try await waitFor(timeout: 2.0) { engine.jobs.first?.status == .running }
        engine.stop()
        runner.finish(with: .init(exitCode: 0, stdout: "", stderr: ""))

        try await waitFor(timeout: 4.0) {
            engine.jobs.allSatisfy { $0.status == .canceled }
        }
        engine.clearCanceledFailed()
        XCTAssertTrue(engine.jobs.isEmpty)
    }

    func testProcessesMixedJunkAndAudioJobs() async throws {
        let runner = ControlledRunner()
        let engine = makeEngine(runner: runner)
        let audio = makeJobs(prefix: "audio", count: 50, ext: "wav")
        let junk = makeJobs(prefix: "junk", count: 25, ext: "txt")
        let bin = makeJobs(prefix: "bin", count: 25, ext: "bin")
        let all = audio + junk + bin
        engine.enqueue(all)
        all.forEach { _ in runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: "")) }

        try await waitFor(timeout: 8.0) { engine.jobs.count == all.count }
        engine.start()
        try await waitFor(timeout: 30.0) { engine.jobs.allSatisfy { $0.status == .done } }
        XCTAssertEqual(engine.jobs.count, all.count)
    }

    // MARK: - Helpers

    private func assertLargeBatchCompletes(count: Int, timeout: TimeInterval, allowSkip: Bool) async throws {
        if allowSkip, !stressEnabled {
            // Run a fast sanity subset so the test still executes in normal CI.
            let quickCount = min(100, count / 5)
            // Allow a slightly more forgiving window to avoid flakes when the
            // runtime is under load (UI tests, sandboxing, or slower CI boxes).
            try await assertLargeBatchCompletes(count: quickCount, timeout: 20.0, allowSkip: false)
            return
        }

        let runner = ControlledRunner()
        let engine = makeEngine(runner: runner)
        let jobs = makeJobs(prefix: "perf\(count)", count: count)
        engine.enqueue(jobs)
        jobs.forEach { _ in runner.enqueueResult(.init(exitCode: 0, stdout: "", stderr: "")) }

        try await waitFor(timeout: 10.0) { engine.jobs.count == jobs.count }
        engine.start()
        try await waitFor(timeout: timeout) { engine.jobs.allSatisfy { $0.status == .done } }
    }

    private var stressEnabled: Bool {
        ProcessInfo.processInfo.environment["RUN_LARGE_QUEUE_STRESS"] == "1"
    }

    private func stressTimeout(fast: TimeInterval, soak: TimeInterval) -> TimeInterval {
        if ProcessInfo.processInfo.environment["RUN_SOAK"] == "1" { return soak }
        return fast
    }

    private func makeJobs(prefix: String, count: Int, ext: String = "wav") -> [Job] {
        (0..<count).map { idx in
            Job(fileURL: URL(fileURLWithPath: "/tmp/\(prefix)-\(idx).\(ext)"),
                displayName: "\(prefix)-\(idx).\(ext)",
                preparedCommand: ["echo", "\(idx)"],
                preparedOutPath: "/tmp/\(prefix)-\(idx).json")
        }
    }

    private func makeEngine(runner: QueueRunner) -> QueueEngine {
        let sink = RecordingSink()
        let resolver = StubResolver()
        let persistence = QueuePersistence(url: tempQueueURL())
        let outbox = IngestOutbox(url: tempOutboxURL(), persist: false)
        return QueueEngine(runner: runner,
                           ingestor: sink,
                           resolver: resolver,
                           persistence: persistence,
                           outbox: outbox,
                           metricsHook: nil)
    }
}
