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
}
