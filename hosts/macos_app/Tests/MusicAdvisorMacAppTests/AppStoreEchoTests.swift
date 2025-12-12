import XCTest
@testable import MusicAdvisorMacApp

@MainActor
final class AppStoreEchoTests: XCTestCase {
    func testSetEchoStatusesAction() {
        let store = AppStore()
        let status = EchoStatus(trackId: "track-1",
                                jobId: "job",
                                status: "done",
                                configHash: "cfg",
                                sourceHash: "src",
                                artifact: "/echo/cfg/src/historical_echo.json",
                                manifest: "/echo/cfg/src/manifest.json",
                                etag: "etag",
                                cachedPath: "/tmp/cache.json",
                                error: nil,
                                neighborCount: 3,
                                decadeSummary: "1990–1999: 1",
                                neighborsPreview: ["a – b"])
        store.dispatch(.setEchoStatuses(["track-1": status]))
        XCTAssertEqual(store.state.echoStatuses["track-1"]?.status, "done")
        XCTAssertEqual(store.state.echoStatuses["track-1"]?.artifact, "/echo/cfg/src/historical_echo.json")
    }

    func testParseEchoSummaryProducesNeighbors() {
        let store = AppStore()
        let payload: [String: Any] = [
            "neighbors": [
                ["artist": "A", "title": "T1", "distance": 0.12],
                ["artist": "B", "title": "T2", "distance": 0.34]
            ],
            "decade_counts": [
                "1990–1999": 1,
                "2000–2009": 2
            ]
        ]
        let data = try! JSONSerialization.data(withJSONObject: payload, options: [])
        let summary = store.parseEchoSummary(data: data)
        XCTAssertEqual(summary.neighborCount, 2)
        XCTAssertEqual(summary.neighborsPreview?.count, 2)
        XCTAssertTrue(summary.decadeSummary?.contains("1990–1999: 1") == true)
        XCTAssertTrue(summary.decadeSummary?.contains("2000–2009: 2") == true)
    }
}
