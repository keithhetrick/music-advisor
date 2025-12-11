import XCTest
@testable import MusicAdvisorMacApp

final class SidecarResolverAdapterTests: XCTestCase {
    func testFinalizeKeepsExistingFinalWhenPresent() {
        let resolver = SidecarResolverAdapter()
        let final = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("json").path
        let temp = final + ".tmp"
        // Seed files
        FileManager.default.createFile(atPath: final, contents: Data("old".utf8))
        FileManager.default.createFile(atPath: temp, contents: Data("new".utf8))

        resolver.finalize(tempPath: temp, finalPath: final)

        let data = FileManager.default.contents(atPath: final)
        let text = data.flatMap { String(data: $0, encoding: .utf8) }
        XCTAssertEqual(text, "old")
        XCTAssertFalse(FileManager.default.fileExists(atPath: temp))
    }

    func testCleanupTempRemovesFile() {
        let resolver = SidecarResolverAdapter()
        let temp = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString).path
        FileManager.default.createFile(atPath: temp, contents: Data("temp".utf8))

        resolver.cleanupTemp(path: temp)

        XCTAssertFalse(FileManager.default.fileExists(atPath: temp))
    }
}
