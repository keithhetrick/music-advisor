import Foundation

struct QueuePersistence {
    struct PersistedJob: Codable {
        var id: UUID
        var filePath: String
        var displayName: String
        var status: String
        var sidecarPath: String?
        var errorMessage: String?
    }

    private let url: URL

    init(url: URL? = nil) {
        self.url = url ?? QueuePersistence.defaultURL()
    }

    func load() -> [Job] {
        guard let data = try? Data(contentsOf: url) else { return [] }
        guard let decoded = try? JSONDecoder().decode([PersistedJob].self, from: data) else { return [] }
        return decoded.compactMap { pj in
            guard let status = Job.Status(rawValue: pj.status) else { return nil }
            let fileURL = URL(fileURLWithPath: pj.filePath)
            var job = Job(id: pj.id, fileURL: fileURL, displayName: pj.displayName, status: status)
            job.sidecarPath = pj.sidecarPath
            job.errorMessage = pj.errorMessage
            return job
        }
    }

    func save(_ jobs: [Job]) {
        let payload: [PersistedJob] = jobs.map { job in
            PersistedJob(id: job.id,
                         filePath: job.fileURL.path,
                         displayName: job.displayName,
                         status: job.status.rawValue,
                         sidecarPath: job.sidecarPath,
                         errorMessage: job.errorMessage)
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
}
