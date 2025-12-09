import Foundation

struct HistoryStore {
    private let url: URL

    init(url: URL? = nil) {
        self.url = url ?? HistoryStore.defaultURL()
    }

    func load() -> [SidecarItem] {
        guard let data = try? Data(contentsOf: url) else { return [] }
        guard let decoded = try? JSONDecoder().decode([SidecarItem].self, from: data) else { return [] }
        return decoded
    }

    /// Background load with optional file-existence filtering. Returns the items and the file mtime.
    func loadAsync(filterExisting: Bool = true, newerThan: Date? = nil) async -> ([SidecarItem], Date?) {
        await withCheckedContinuation { cont in
            DispatchQueue.global(qos: .utility).async {
                let mtime = modificationDate()
                if let newerThan, let mtime, mtime <= newerThan {
                    cont.resume(returning: ([], mtime))
                    return
                }
                var items = load()
                if filterExisting {
                    let fm = FileManager.default
                    items = items.filter { fm.fileExists(atPath: $0.path) }
                }
                cont.resume(returning: (items, mtime))
            }
        }
    }

    func save(_ items: [SidecarItem]) {
        do {
            let data = try JSONEncoder().encode(items)
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(),
                                                    withIntermediateDirectories: true,
                                                    attributes: nil)
            try data.write(to: url, options: .atomic)
        } catch {
            // best effort
        }
    }

    private static func defaultURL() -> URL {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        return appDir.appendingPathComponent("history.json")
    }

    private func modificationDate() -> Date? {
        (try? FileManager.default.attributesOfItem(atPath: url.path)[.modificationDate] as? Date) ?? nil
    }
}
