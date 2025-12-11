import XCTest
@testable import MAQueue

final class JobModelCoverageTests: XCTestCase {
    func testJobInitAndProperties() {
        let id = UUID()
        let job = Job(id: id,
                      fileURL: URL(fileURLWithPath: "/tmp/track.mp3"),
                      displayName: "Track",
                      groupID: UUID(),
                      groupName: "Group",
                      groupRootPath: "/tmp",
                      status: .pending,
                      sidecarPath: "/tmp/sidecar.json",
                      errorMessage: "Err",
                      attempts: 1)

        XCTAssertEqual(job.id, id)
        XCTAssertEqual(job.displayName, "Track")
        XCTAssertEqual(job.status, Job.Status.pending)
        XCTAssertEqual(job.attempts, 1)
        XCTAssertEqual(job.errorMessage, "Err")
        XCTAssertEqual(job.sidecarPath, "/tmp/sidecar.json")
        XCTAssertEqual(job.groupName, "Group")
        XCTAssertEqual(job.groupRootPath, "/tmp")
    }

    func testJobProgressAcrossStatuses() {
        let pending = Job(fileURL: URL(fileURLWithPath: "/tmp/p.wav"), displayName: "p", status: .pending)
        var running = Job(fileURL: URL(fileURLWithPath: "/tmp/r.wav"), displayName: "r", status: .pending)
        running.status = .running
        var done = Job(fileURL: URL(fileURLWithPath: "/tmp/d.wav"), displayName: "d", status: .pending)
        done.status = .done
        var failed = Job(fileURL: URL(fileURLWithPath: "/tmp/f.wav"), displayName: "f", status: .pending)
        failed.status = .failed
        var canceled = Job(fileURL: URL(fileURLWithPath: "/tmp/c.wav"), displayName: "c", status: .pending)
        canceled.status = .canceled

        XCTAssertEqual(pending.progress, 0.0)
        XCTAssertEqual(running.progress, 0.5)
        XCTAssertEqual(done.progress, 1.0)
        XCTAssertEqual(failed.progress, 1.0)
        XCTAssertEqual(canceled.progress, 1.0)

        // Hashable/Equatable smoke
        let set = Set([pending, pending])
        XCTAssertEqual(set.count, 1)
    }
}
