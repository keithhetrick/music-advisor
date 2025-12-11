import XCTest
@testable import MAQueue

final class QueuePersistenceTests: XCTestCase {
    private var tempURL: URL!

    override func setUp() {
        super.setUp()
        let tmpDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try? FileManager.default.createDirectory(at: tmpDir, withIntermediateDirectories: true)
        tempURL = tmpDir.appendingPathComponent("queue.json")
    }

    func testSaveAndLoadPreservesCanceled() {
        let persistence = QueuePersistence(url: tempURL)
        let canceled = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", status: .canceled, errorMessage: "Canceled by user")
        persistence.save([canceled])

        let loaded = persistence.load()

        XCTAssertEqual(loaded.count, 1)
        XCTAssertEqual(loaded.first?.status, .canceled)
        XCTAssertEqual(loaded.first?.errorMessage, "Canceled by user")
    }

    func testLoadNormalizesRunningToFailed() {
        let persistence = QueuePersistence(url: tempURL)
        let running = Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", status: .running, errorMessage: nil)
        persistence.save([running])

        let loaded = persistence.load()

        XCTAssertEqual(loaded.first?.status, .failed)
        XCTAssertEqual(loaded.first?.errorMessage, "Interrupted during previous session")
    }

    func testGroupMetadataPersists() {
        let persistence = QueuePersistence(url: tempURL)
        let groupID = UUID()
        let job = Job(id: UUID(),
                      fileURL: URL(fileURLWithPath: "/tmp/a.wav"),
                      displayName: "a",
                      groupID: groupID,
                      groupName: "Folder",
                      groupRootPath: "/tmp",
                      status: .pending,
                      sidecarPath: "/tmp/out.json",
                      errorMessage: nil,
                      preparedCommand: ["echo", "hi"],
                      preparedOutPath: "/tmp/out.json")
        persistence.save([job])

        let loaded = persistence.load()

        XCTAssertEqual(loaded.first?.groupID, groupID)
        XCTAssertEqual(loaded.first?.groupName, "Folder")
        XCTAssertEqual(loaded.first?.groupRootPath, "/tmp")
        XCTAssertEqual(loaded.first?.preparedCommand ?? [], ["echo", "hi"])
        XCTAssertEqual(loaded.first?.preparedOutPath, "/tmp/out.json")
    }

    func testCorruptFileReturnsEmpty() throws {
        let badData = Data("not-json".utf8)
        try badData.write(to: tempURL)
        let persistence = QueuePersistence(url: tempURL)

        let loaded = persistence.load()

        XCTAssertTrue(loaded.isEmpty)
    }

    func testPartialMixedStatesRoundTrip() {
        let persistence = QueuePersistence(url: tempURL)
        let running = Job(fileURL: URL(fileURLWithPath: "/tmp/run.wav"), displayName: "run", status: .running, errorMessage: nil)
        let canceled = Job(fileURL: URL(fileURLWithPath: "/tmp/can.wav"), displayName: "can", status: .canceled, errorMessage: "user")
        let done = Job(fileURL: URL(fileURLWithPath: "/tmp/done.wav"), displayName: "done", status: .done, errorMessage: nil)
        persistence.save([running, canceled, done])

        let loaded = persistence.load()

        XCTAssertEqual(loaded.count, 3)
        XCTAssertEqual(loaded[0].status, .failed) // running should normalize
        XCTAssertEqual(loaded[1].status, .canceled)
        XCTAssertEqual(loaded[1].errorMessage, "user")
        XCTAssertEqual(loaded[2].status, .done)
    }

    func testMalformedJSONFailsClosed() throws {
        let malformed = """
        [
          {"fileURL":"/tmp/a.wav","displayName":"a","status":"pending","unexpected":"x"},
          {"displayName":"b","status":"done"}
        ]
        """
        try malformed.data(using: .utf8)?.write(to: tempURL)
        let persistence = QueuePersistence(url: tempURL)

        let loaded = persistence.load()

        XCTAssertTrue(loaded.isEmpty)
    }
}
