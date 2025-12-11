import Foundation

public protocol IngestSink: AnyObject {
    func ingest(fileURL: URL, jobID: UUID?) async -> Bool
}

public actor IngestOutbox {
    public struct Entry: Codable, Identifiable {
        public let id: UUID
        public let jobID: UUID?
        public let filePath: String
        public var attempts: Int
        public var lastAttempt: Date?
        public var lastError: String?
    }

    private var entries: [Entry] = []
    private let url: URL
    private let persist: Bool
    private let dateProvider: @Sendable () -> Date

    public init(url: URL? = nil,
                persist: Bool = true,
                dateProvider: @escaping @Sendable () -> Date = { Date() }) {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        self.url = url ?? appDir.appendingPathComponent("ingest_outbox.json")
        self.persist = persist
        self.dateProvider = dateProvider
        Task { await load() }
    }

    public func enqueue(fileURL: URL, jobID: UUID?) {
        let path = fileURL.path
        guard !entries.contains(where: { $0.filePath == path }) else { return }
        let entry = Entry(id: UUID(), jobID: jobID, filePath: path, attempts: 0, lastAttempt: nil, lastError: nil)
        entries.append(entry)
        QueueLogger.shared.log(.debug, "outbox enqueue file=\(path)")
        save()
    }

    public func snapshot() -> (pending: Int, errors: Int) {
        let pending = entries.count
        let errors = entries.filter { $0.lastError != nil }.count
        return (pending, errors)
    }

    func nextPending() -> Entry? {
        let now = dateProvider()
        return entries.first { entry in
            if entry.attempts >= 5 { return false }
            if let last = entry.lastAttempt {
                let delay = min(pow(2.0, Double(entry.attempts)), 60.0)
                return now.timeIntervalSince(last) >= delay
            }
            return true
        }
    }

    func markSuccess(id: UUID) {
        if let idx = entries.firstIndex(where: { $0.id == id }) {
            entries.remove(at: idx)
            QueueLogger.shared.log(.debug, "outbox success id=\(id)")
            save()
        }
    }

    func markFailure(id: UUID, error: String) {
        if let idx = entries.firstIndex(where: { $0.id == id }) {
            entries[idx].attempts += 1
            entries[idx].lastAttempt = dateProvider()
            entries[idx].lastError = error
            QueueLogger.shared.log(.error, "outbox failure id=\(id) err=\(error)")
            save()
        }
    }

    func pendingCount() -> Int {
        entries.count
    }

    private func load() async {
        guard persist else { return }
        guard let data = try? Data(contentsOf: url) else { return }
        if let decoded = try? JSONDecoder().decode([Entry].self, from: data) {
            entries = decoded
            QueueLogger.shared.log(.debug, "outbox load count=\(entries.count)")
        }
    }

    private func save() {
        guard persist else { return }
        do {
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(entries)
            try data.write(to: url, options: .atomic)
        } catch {
            // best-effort; ignore
        }
    }
}

public final class IngestProcessor {
    private let outbox: IngestOutbox
    private weak var sink: IngestSink?
    private var isProcessing = false
    private let onMetrics: (() -> Void)?

    public init(outbox: IngestOutbox, sink: IngestSink?, onMetrics: (() -> Void)? = nil) {
        self.outbox = outbox
        self.sink = sink
        self.onMetrics = onMetrics
    }

    public func kick() {
        guard !isProcessing else { return }
        isProcessing = true
        Task {
            await processLoop()
            isProcessing = false
        }
    }

    private func processLoop() async {
        while let entry = await outbox.nextPending() {
            let success = await ingest(entry)
            if success {
                await outbox.markSuccess(id: entry.id)
            } else {
                await outbox.markFailure(id: entry.id, error: "ingest failed")
            }
        }
        if let onMetrics {
            await MainActor.run {
                onMetrics()
            }
        }
    }

    @MainActor
    private func ingest(_ entry: IngestOutbox.Entry) async -> Bool {
        guard let sink else { return false }
        let url = URL(fileURLWithPath: entry.filePath)
        return await sink.ingest(fileURL: url, jobID: entry.jobID)
    }
}
