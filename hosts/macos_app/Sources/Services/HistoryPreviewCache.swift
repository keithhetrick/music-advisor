import Foundation

struct HistoryPreviewCache {
    struct PersistedPreview: Codable {
        var path: String
        var sidecar: String
        var rich: String?
        var richFound: Bool
        var richPath: String?
        var modified: Date?
    }

    private let url: URL
    private let maxEntries: Int = 20

    init(url: URL? = nil) {
        self.url = url ?? HistoryPreviewCache.defaultURL()
    }

    func load() -> [String: (HistoryPreview, Date?)] {
        guard let data = try? Data(contentsOf: url) else { return [:] }
        guard let decoded = try? JSONDecoder().decode([PersistedPreview].self, from: data) else { return [:] }
        var result: [String: (HistoryPreview, Date?)] = [:]
        for entry in decoded {
            let preview = HistoryPreview(sidecar: entry.sidecar,
                                         rich: entry.rich,
                                         richFound: entry.richFound,
                                         richPath: entry.richPath)
            result[entry.path] = (preview, entry.modified)
        }
        return result
    }

    func loadAsync(filterExisting: Bool = true) async -> [String: (HistoryPreview, Date?)] {
        await withCheckedContinuation { cont in
            DispatchQueue.global(qos: .utility).async {
                var loaded = load()
                if filterExisting {
                    let fm = FileManager.default
                    loaded = loaded.filter { fm.fileExists(atPath: $0.key) }
                }
                cont.resume(returning: loaded)
            }
        }
    }

    func save(_ cache: [String: (HistoryPreview, Date?)]) {
        Task.detached(priority: .utility) {
            // Keep only most recent entries by modification date if available, else by name.
            let sorted = cache.sorted { lhs, rhs in
                let ldate = lhs.value.1 ?? Date.distantPast
                let rdate = rhs.value.1 ?? Date.distantPast
                return ldate > rdate
            }
            let trimmed = sorted.prefix(maxEntries)
            let payload: [PersistedPreview] = trimmed.map { key, value in
                PersistedPreview(path: key,
                                 sidecar: value.0.sidecar,
                                 rich: value.0.rich,
                                 richFound: value.0.richFound,
                                 richPath: value.0.richPath,
                                 modified: value.1)
            }
            do {
                let data = try JSONEncoder().encode(payload)
                try FileManager.default.createDirectory(at: url.deletingLastPathComponent(),
                                                        withIntermediateDirectories: true,
                                                        attributes: nil)
                try data.write(to: url, options: .atomic)
            } catch {
                // Best-effort cache; ignore failures.
            }
        }
    }

    private static func defaultURL() -> URL {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        return appDir.appendingPathComponent("preview_cache.json")
    }
}
