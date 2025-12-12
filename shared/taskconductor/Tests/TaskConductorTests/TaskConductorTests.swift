import XCTest
@testable import TaskConductor

final class TaskConductorTests: XCTestCase {
    private let eventQueue = DispatchQueue(label: "events.common")

    // Small helper to avoid mutating captured vars on concurrent queues in tests.
    private final class Locked<Value> {
        private let queue = DispatchQueue(label: "taskconductor.locked." + UUID().uuidString)
        private var value: Value

        init(_ value: Value) {
            self.value = value
        }

        func get() -> Value {
            queue.sync { value }
        }

        func set(_ newValue: Value) {
            queue.sync { value = newValue }
        }

        func mutate(_ block: (inout Value) -> Void) {
            queue.sync { block(&value) }
        }
    }

    // MARK: - Smoke + lifecycle

    func testEchoCompletes() {
        let broker = TaskConductor()
        let finished = expectation(description: "finished")
        let sawHello = expectation(description: "saw hello")

        Task {
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/echo", "hello"])) { event in
                self.eventQueue.sync {
                    switch event {
                    case .stdout(_, let line):
                        if line == "hello" { sawHello.fulfill() }
                    case .finished:
                        finished.fulfill()
                    default:
                        break
                    }
                }
            }
        }

        wait(for: [finished, sawHello], timeout: 5)
    }

    func testTimeoutTerminatesTask() {
        let broker = TaskConductor()
        let timedOut = expectation(description: "timed out")
        final class Flag { var value = false }
        let sawTimeout = Flag()

        Task {
            _ = await broker.enqueue(
                TaskDescriptor(
                    command: ["/bin/sleep", "2"],
                    timeoutSeconds: 0.2
                )
            ) { event in
                self.eventQueue.sync {
                    if case .timeout = event {
                        sawTimeout.value = true
                        timedOut.fulfill()
                    }
                }
            }
        }

        wait(for: [timedOut], timeout: 5)
        eventQueue.sync {
            XCTAssertTrue(sawTimeout.value, "Did not observe timeout event")
        }
    }

    func testCancelTerminatesTask() {
        let broker = TaskConductor()
        let canceled = expectation(description: "canceled")
        final class HandleBox { var handle: TaskConductor.Handle? }
        let handleBox = HandleBox()
        final class Flag { var value = false }
        let sawCancel = Flag()
        let handleReady = DispatchSemaphore(value: 0)

        Task {
            handleBox.handle = await broker.enqueue(TaskDescriptor(command: ["/bin/sleep", "5"])) { event in
                self.eventQueue.sync {
                    if case .canceled = event {
                        sawCancel.value = true
                        canceled.fulfill()
                    }
                }
            }
            handleReady.signal()
        }

        // Allow process to start, then cancel
        handleReady.wait()
        usleep(200_000)
        if let id = handleBox.handle?.id {
            Task { await broker.cancel(id: id) { _ in } }
        }

        wait(for: [canceled], timeout: 5)
        eventQueue.sync {
            XCTAssertTrue(sawCancel.value, "Did not observe canceled event")
        }
    }

    // MARK: - Scheduling and limits

    func testMaxConcurrencyHonored() {
        let broker = TaskConductor(config: .init(maxConcurrentTasks: 1))
        let finished = expectation(description: "both finished")
        finished.expectedFulfillmentCount = 2
        final class Counter { var maxRunning = 0; var current = 0 }
        let counter = Counter()

        Task {
            for _ in 0..<2 {
                _ = await broker.enqueue(TaskDescriptor(command: ["/bin/sleep", "0.3"])) { event in
                    self.eventQueue.sync {
                        switch event {
                        case .started:
                            counter.current += 1
                            counter.maxRunning = max(counter.maxRunning, counter.current)
                        case .finished, .failed, .timeout, .canceled:
                            counter.current -= 1
                            finished.fulfill()
                        default:
                            break
                        }
                    }
                }
            }
        }

        wait(for: [finished], timeout: 5)
        eventQueue.sync {
            XCTAssertLessThanOrEqual(counter.maxRunning, 1, "More than one task ran concurrently")
        }
    }

    func testLargeBatchRespectsConcurrencyAndFinishes() async {
        let broker = TaskConductor(config: .init(maxConcurrentTasks: 2))
        let total = 20
        let done = expectation(description: "finished batch")
        done.expectedFulfillmentCount = total

        actor RunningCounter {
            private var current = 0
            private var maxSeen = 0
            func inc() { current += 1; maxSeen = Swift.max(maxSeen, current) }
            func dec() { current -= 1 }
            func peak() -> Int { maxSeen }
        }
        let counter = RunningCounter()

        for i in 0..<total {
            Task {
                _ = await broker.enqueue(
                    TaskDescriptor(command: ["/bin/sh", "-c", "sleep 0.05; echo \(i)"])
                ) { event in
                    Task {
                        switch event {
                        case .started:
                            await counter.inc()
                        case .finished, .failed, .timeout, .canceled:
                            await counter.dec()
                            done.fulfill()
                        default:
                            break
                        }
                    }
                }
            }
        }

        wait(for: [done], timeout: 10)
        let maxRunning = await counter.peak()
        XCTAssertLessThanOrEqual(maxRunning, 2, "Concurrency cap should be honored")
    }

    func testQueueDepthRejects() {
        let broker = TaskConductor(config: .init(maxConcurrentTasks: 1, maxQueueDepth: 0))
        let internalErr = expectation(description: "queue full error")

        Task {
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/sleep", "0.1"])) { _ in }
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/echo", "late"])) { event in
                self.eventQueue.sync {
                    if case .internalError(_, let msg) = event, msg.contains("Queue full") {
                        internalErr.fulfill()
                    }
                }
            }
        }

        wait(for: [internalErr], timeout: 5)
    }

    func testFailureDoesNotBlockSubsequentTask() {
        let broker = TaskConductor(config: .init(maxConcurrentTasks: 1, retryCount: 0))
        let failed = expectation(description: "saw failed")
        let echoed = expectation(description: "echoed")

        Task {
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/sh", "-c", "exit 2"])) { event in
                self.eventQueue.sync {
                    if case .failed = event { failed.fulfill() }
                }
            }
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/echo", "hi"])) { event in
                self.eventQueue.sync {
                    switch event {
                    case .started:
                        // Seeing start proves the queue advanced beyond the failed task.
                        echoed.fulfill()
                    case .stdout(_, let line):
                        if line.trimmingCharacters(in: .whitespacesAndNewlines) == "hi" {
                            echoed.fulfill()
                        }
                    case .finished:
                        // If stdout filtering ever missed, finishing still proves we progressed past the failed task.
                        echoed.fulfill()
                    default:
                        break
                    }
                }
            }
        }

        wait(for: [failed, echoed], timeout: 15)
    }

    // MARK: - Retry + logging

    func testRetryLogicEmitsRetryingAndFinishes() {
        let broker = TaskConductor(config: .init(retryCount: 1, retryDelaySeconds: 0.05))
        let retrying = expectation(description: "retrying")
        let failed = expectation(description: "failed after retry")

        Task {
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/sh", "-c", "exit 1"])) { event in
                self.eventQueue.sync {
                    switch event {
                    case .retrying:
                        retrying.fulfill()
                    case .failed:
                        failed.fulfill()
                    default:
                        break
                    }
                }
            }
        }

        wait(for: [retrying, failed], timeout: 5)
    }

    func testRetryJitterStaysWithinRange() {
        let base: TimeInterval = 0.20
        let jitter: TimeInterval = 0.05
        let broker = TaskConductor(config: .init(
            retryCount: 1,
            retryDelaySeconds: base,
            retryJitterSeconds: jitter
        ))
        let retrying = expectation(description: "retrying")
        let failed = expectation(description: "failed")
        let observedDelay = Locked<TimeInterval?>(nil)

        Task {
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/sh", "-c", "exit 1"])) { event in
                self.eventQueue.sync {
                    switch event {
                    case .retrying(_, _, let delay):
                        observedDelay.set(delay)
                        retrying.fulfill()
                    case .failed:
                        failed.fulfill()
                    default:
                        break
                    }
                }
            }
        }

        wait(for: [retrying, failed], timeout: 5)
        let delay = observedDelay.get()
        XCTAssertNotNil(delay, "Expected to capture a retry delay")
        if let delay {
            // Allow a small epsilon for scheduling / timer drift.
            XCTAssertTrue(
                delay >= (base - jitter - 0.01) && delay <= (base + jitter + 0.01),
                "Delay \(delay) not within jittered range"
            )
        }
    }

    func testLogLineHandlerMirrorsOutput() {
        let captured = Locked<[String]>([])
        let finished = expectation(description: "finished")

        let broker = TaskConductor(config: .init(
            maxConcurrentTasks: 1,
            logLineHandler: { line in
                captured.mutate { $0.append(line) }
            }
        ))

        Task {
            _ = await broker.enqueue(
                TaskDescriptor(command: ["/bin/sh", "-c", "echo first; echo second"])
            ) { event in
                self.eventQueue.sync {
                    if case .finished = event {
                        finished.fulfill()
                    }
                }
            }
        }

        wait(for: [finished], timeout: 5)
        let lines = captured.get().joined(separator: "\n")
        XCTAssertTrue(lines.contains("first"), "Log handler should see stdout lines")
        XCTAssertTrue(lines.contains("second"), "Log handler should see stdout lines")
    }

    func testExtraLogHandlerInvoked() {
        final class LogState {
            var captured: [TaskEvent] = []
            var startedSeen = false
            var finishedSeen = false
        }
        let state = LogState()
        let logQueue = DispatchQueue(label: "taskconductor.extraLog")
        let startedExpectation = expectation(description: "saw started")
        let finishedExpectation = expectation(description: "saw finished")

        let broker = TaskConductor(config: .init(
            maxConcurrentTasks: 1,
            extraLogHandler: { event in
                logQueue.sync {
                    state.captured.append(event)
                    switch event {
                    case .started where !state.startedSeen:
                        state.startedSeen = true
                        startedExpectation.fulfill()
                    case .finished where !state.finishedSeen:
                        state.finishedSeen = true
                        finishedExpectation.fulfill()
                    default:
                        break
                    }
                }
            }
        ))

        Task {
            _ = await broker.enqueue(TaskDescriptor(command: ["/bin/echo", "hi"])) { _ in }
        }

        wait(for: [startedExpectation, finishedExpectation], timeout: 5)
        logQueue.sync {
            XCTAssertTrue(state.captured.contains { if case .finished = $0 { return true } else { return false } })
        }
    }

    func testMixedClientsUseIsolatedEnvAndWorkdir() async throws {
        let fm = FileManager.default
        let tmpRoot = fm.temporaryDirectory
        let dir1 = tmpRoot.appendingPathComponent(UUID().uuidString)
        let dir2 = tmpRoot.appendingPathComponent(UUID().uuidString)
        try fm.createDirectory(at: dir1, withIntermediateDirectories: true)
        try fm.createDirectory(at: dir2, withIntermediateDirectories: true)

        let broker = TaskConductor(config: .init(maxConcurrentTasks: 1))

        let finished = expectation(description: "finished both")
        finished.expectedFulfillmentCount = 2

        // Capture stdout per client via an actor to stay Swift 6-safe.
        actor SafeStore {
            private var clientById: [UUID: String] = [:]
            private var outputs: [String: [String]] = [:]

            func setClient(id: UUID, marker: String) {
                clientById[id] = marker
            }

            func append(id: UUID, line: String) {
                guard let who = clientById[id] else { return }
                outputs[who, default: []].append(line)
            }

            func outputs(for marker: String) -> [String] {
                outputs[marker, default: []]
            }
        }

        let store = SafeStore()

        func enqueueClient(marker: String, workdir: URL) {
            Task {
                let handle = await broker.enqueue(
                    TaskDescriptor(
                        command: ["/bin/sh", "-c", "echo $CLIENT && pwd"],
                        workingDirectory: workdir.path,
                        environment: ["CLIENT": marker]
                    )
                ) { event in
                    Task {
                        switch event {
                        case .stdout(let id, let rawLine):
                            let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
                            await store.append(id: id, line: line)
                        case .finished:
                            finished.fulfill()
                        default:
                            break
                        }
                    }
                }
                await store.setClient(id: handle.id, marker: marker)
            }
        }

        enqueueClient(marker: "A", workdir: dir1)
        enqueueClient(marker: "B", workdir: dir2)

        wait(for: [finished], timeout: 10)
        let a = await store.outputs(for: "A")
        let b = await store.outputs(for: "B")
        XCTAssertGreaterThanOrEqual(a.count, 1, "client A should emit stdout")
        XCTAssertGreaterThanOrEqual(b.count, 1, "client B should emit stdout")
        XCTAssertTrue(a.contains { $0.contains("A") })
        XCTAssertTrue(b.contains { $0.contains("B") })
        XCTAssertTrue(a.contains { $0.contains(dir1.lastPathComponent) || $0.contains(dir1.path) })
        XCTAssertTrue(b.contains { $0.contains(dir2.lastPathComponent) || $0.contains(dir2.path) })
    }
}
