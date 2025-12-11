import Foundation

public struct QueuePersistence {
    public struct PersistedJob: Codable {
        public var id: UUID
        public var filePath: String
        public var displayName: String
        public var status: String
        public var sidecarPath: String?
        public var errorMessage: String?
        public var groupID: UUID?
        public var groupName: String?
        public var groupRootPath: String?
        public var preparedCommand: [String]?
        public var preparedOutPath: String?
        public var createdAt: Date?
        public var updatedAt: Date?
        public var startedAt: Date?
        public var finishedAt: Date?
        public var attempts: Int?
    }

    private let url: URL

    public init(url: URL? = nil) {
        self.url = url ?? QueuePersistence.defaultURL()
    }

    public func load() -> [Job] {
        QueueLogger.shared.log(.debug, "persistence load from \(url.path)")
        guard let data = try? Data(contentsOf: url) else {
            QueueLogger.shared.log(.debug, "persistence load skipped (no data)")
            return []
        }
        guard let decoded = try? JSONDecoder().decode([PersistedJob].self, from: data) else {
            QueueLogger.shared.log(.error, "persistence decode failed, dropping file")
            return []
        }
        let jobs: [Job] = decoded.compactMap { pj in
            guard let persistedStatus = Job.Status(rawValue: pj.status) else { return nil }
            let status: Job.Status
            var errorMessage = pj.errorMessage
            var finishedAt = pj.finishedAt
            var updatedAt = pj.updatedAt ?? pj.createdAt ?? Date()
            // Normalize any in-flight jobs after restart so they don't resurrect.
            if persistedStatus == .running {
                status = .failed
                errorMessage = errorMessage ?? "Interrupted during previous session"
                finishedAt = finishedAt ?? Date()
                updatedAt = Date()
            } else {
                status = persistedStatus
            }
            let fileURL = URL(fileURLWithPath: pj.filePath)
            return Job(id: pj.id,
                       fileURL: fileURL,
                       displayName: pj.displayName,
                       groupID: pj.groupID,
                       groupName: pj.groupName,
                       groupRootPath: pj.groupRootPath,
                       status: status,
                       sidecarPath: pj.sidecarPath,
                       errorMessage: errorMessage,
                       preparedCommand: pj.preparedCommand,
                       preparedOutPath: pj.preparedOutPath,
                       createdAt: pj.createdAt ?? Date(),
                       updatedAt: updatedAt,
                       startedAt: pj.startedAt,
                       finishedAt: finishedAt,
                       attempts: pj.attempts ?? 0)
        }
        QueueLogger.shared.log(.debug, "persistence load restored count=\(jobs.count) \(statusSummary(jobs))")
        return jobs
    }

    public func save(_ jobs: [Job]) {
        QueueLogger.shared.log(.debug, "persistence save count=\(jobs.count) \(statusSummary(jobs)) to \(url.path)")
        let payload: [PersistedJob] = jobs.map { job in
            PersistedJob(id: job.id,
                         filePath: job.fileURL.path,
                         displayName: job.displayName,
                         status: job.status.rawValue,
                         sidecarPath: job.sidecarPath,
                         errorMessage: job.errorMessage,
                         groupID: job.groupID,
                         groupName: job.groupName,
                         groupRootPath: job.groupRootPath,
                         preparedCommand: job.preparedCommand,
                         preparedOutPath: job.preparedOutPath,
                         createdAt: job.createdAt,
                         updatedAt: job.updatedAt,
                         startedAt: job.startedAt,
                         finishedAt: job.finishedAt,
                         attempts: job.attempts)
        }
        do {
            let data = try JSONEncoder().encode(payload)
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(),
                                                    withIntermediateDirectories: true,
                                                    attributes: nil)
            try data.write(to: url, options: .atomic)
        } catch {
            // Intentionally silent; persistence is best-effort for UX.
        }
    }

    private static func defaultURL() -> URL {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        return appDir.appendingPathComponent("queue.json")
    }

    private func statusSummary(_ jobs: [Job]) -> String {
        var counts: [Job.Status: Int] = [:]
        for job in jobs {
            counts[job.status, default: 0] += 1
        }
        return "pending=\(counts[.pending, default: 0]) running=\(counts[.running, default: 0]) done=\(counts[.done, default: 0]) failed=\(counts[.failed, default: 0]) canceled=\(counts[.canceled, default: 0])"
    }

    public func statusSummaryLine(_ jobs: [Job]) -> String {
        statusSummary(jobs)
    }
}
