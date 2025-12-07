import Foundation

enum SpecialActions {
    static func sidecarDirectory() -> URL {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return supportDir.appendingPathComponent("MusicAdvisorMacApp/sidecars", isDirectory: true)
    }

    static func clearSidecarsOnDisk() throws {
        let dir = sidecarDirectory()
        if FileManager.default.fileExists(atPath: dir.path) {
            try FileManager.default.removeItem(at: dir)
        }
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    }
}
