import Foundation
import XCTest
@testable import MAQueue
@testable import MusicAdvisorMacApp

// Shared test doubles and helpers across Queue/History tests.

// MARK: - Queue runner double

@MainActor
final class ControlledRunner: QueueRunner {
    private var continuation: CheckedContinuation<QueueRunResult, Never>?
    private var queuedResults: [QueueRunResult] = []
    var hold: Bool = false

    func enqueueResult(_ result: QueueRunResult) {
        queuedResults.append(result)
    }

    func run(job: Job) async -> QueueRunResult {
        if !hold, let next = queuedResults.first {
            queuedResults.removeFirst()
            return next
        }
        return await withCheckedContinuation { cont in
            continuation = cont
        }
    }

    func finish(with result: QueueRunResult) {
        if let cont = continuation {
            cont.resume(returning: result)
            continuation = nil
            return
        }
        queuedResults.append(result)
    }
}

// MARK: - Ingest / resolver doubles

final class RecordingSink: IngestSink {
    struct IngestCall: Equatable {
        let path: String
        let jobID: UUID?
    }

    private(set) var ingested: [IngestCall] = []

    func ingest(fileURL: URL, jobID: UUID?) async -> Bool {
        ingested.append(.init(path: fileURL.path, jobID: jobID))
        return true
    }
}

struct StubResolver: SidecarResolver {
    func ensureSidecar(for job: Job) -> (final: String, temp: String) {
        let final = job.preparedOutPath ?? "/tmp/\(UUID().uuidString).json"
        return (final, final + ".tmp")
    }

    func cleanupTemp(path: String?) {}
    func finalize(tempPath: String?, finalPath: String?) {}
}

final class RecordingResolver: SidecarResolver {
    private(set) var finalizedCalled = false
    private(set) var finalFileExists = false
    private(set) var cleanupCalled = false

    func ensureSidecar(for job: Job) -> (final: String, temp: String) {
        let final = job.preparedOutPath ?? FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("json")
            .path
        let temp = final + ".tmp"
        FileManager.default.createFile(atPath: temp, contents: Data("temp".utf8))
        return (final, temp)
    }

    func cleanupTemp(path: String?) {
        cleanupCalled = true
        if let path, FileManager.default.fileExists(atPath: path) {
            try? FileManager.default.removeItem(atPath: path)
        }
    }

    func finalize(tempPath: String?, finalPath: String?) {
        finalizedCalled = true
        guard let tempPath, let finalPath else { return }
        try? FileManager.default.removeItem(atPath: finalPath)
        try? FileManager.default.moveItem(atPath: tempPath, toPath: finalPath)
        finalFileExists = FileManager.default.fileExists(atPath: finalPath)
    }
}

// MARK: - History resolver

final class HistoryResolver: SidecarResolver {
    let historyStore: HistoryStore
    init(historyStore: HistoryStore) {
        self.historyStore = historyStore
    }
    func ensureSidecar(for job: Job) -> (final: String, temp: String) {
        let final = job.preparedOutPath ?? "/tmp/\(UUID().uuidString).json"
        return (final, final + ".tmp")
    }
    func cleanupTemp(path: String?) {}
    func finalize(tempPath: String?, finalPath: String?) {
        var items = historyStore.load()
        items.append(SidecarItem(path: finalPath ?? "",
                                 name: "history-item",
                                 modified: Date()))
        historyStore.save(items)
    }
}

// MARK: - Temp URLs

func tempQueueURL() -> URL {
    FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("queue.json")
}

func tempOutboxURL() -> URL {
    FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("outbox.json")
}

func tempHistoryURL() -> URL {
    FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("history.json")
}

// MARK: - Wait helper

func waitFor(timeout: TimeInterval = 5.0, condition: @escaping () -> Bool) async throws {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        if condition() { return }
        try await Task.sleep(nanoseconds: 20_000_000)
    }
    XCTFail("Condition not met within \(timeout) seconds")
}
