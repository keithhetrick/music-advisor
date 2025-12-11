import XCTest
@testable import MusicAdvisorMacApp
@testable import MAQueue

@MainActor
final class HistoryPersistenceTests: XCTestCase {
    func testCompletedJobPersistsToHistoryStore() async throws {
        let historyStore = HistoryStore(url: tempHistoryURL())
        let persistence = QueuePersistence(url: tempQueueURL())
        let outbox = IngestOutbox(url: tempOutboxURL())
        let runner = ControlledRunner()
        let ingestor = RecordingSink()
        let resolver = HistoryResolver(historyStore: historyStore)

        let engine = QueueEngine(runner: runner,
                                 ingestor: ingestor,
                                 resolver: resolver,
                                 persistence: persistence,
                                 outbox: outbox,
                                 metricsHook: nil)

        let job = Job(fileURL: URL(fileURLWithPath: "/tmp/hist.wav"),
                      displayName: "hist",
                      preparedCommand: ["echo", "done"],
                      preparedOutPath: "/tmp/hist.json")
        engine.enqueue([job])
        runner.enqueueResult(.init(exitCode: 0, stdout: "ok", stderr: ""))

        try await waitFor(timeout: 0.5) { engine.jobs.count == 1 }
        engine.start()
        try await waitFor(timeout: 1.0) { engine.jobs.first?.status == .done }

        let items = historyStore.load()
        XCTAssertEqual(items.count, 1)
        XCTAssertEqual(items.first?.path, job.preparedOutPath ?? "")
    }
}
