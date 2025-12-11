import XCTest
import ViewInspector
@testable import MAQueue
@testable import MusicAdvisorMacApp

@MainActor
final class JobQueueViewSnapshotTests: XCTestCase {
    private func makeJob(_ status: Job.Status) -> Job {
        Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", status: status)
    }

    func testHeaderShowsQueuedBadge() throws {
        let view = JobQueueView(
            jobs: [makeJob(.pending)],
            isEnqueuing: false,
            onReveal: { _ in },
            onPreviewRich: { _ in },
            onClear: {}
        )

        let header = try view.inspect().vStack().hStack(0)
        let badge = try header.find(text: "Queued")
        XCTAssertEqual(try badge.string(), "Queued")
    }

    func testStopAndCancelButtonsVisibility() throws {
        let view = JobQueueView(
            jobs: [makeJob(.pending)],
            isEnqueuing: false,
            onReveal: { _ in },
            onPreviewRich: { _ in },
            onClear: {},
            onStop: {},
            onCancelPending: {}
        )

        let header = try view.inspect().vStack().hStack(0)
        XCTAssertNotNil(try header.find(button: "Stop"))
        XCTAssertNotNil(try header.find(button: "Cancel pending"))
    }

    func testResumeCanceledButtonVisibleWhenCanceledJobExists() throws {
        let view = JobQueueView(
            jobs: [makeJob(.canceled)],
            isEnqueuing: false,
            onReveal: { _ in },
            onPreviewRich: { _ in },
            onClear: {},
            onResumeCanceled: {}
        )

        let header = try view.inspect().vStack().hStack(0)
        XCTAssertNotNil(try header.find(button: "Resume canceled"))
    }

    func testGroupedFoldersSnapshot() throws {
        let groupID = UUID()
        let jobs = [
            Job(fileURL: URL(fileURLWithPath: "/tmp/folder/song1.wav"),
                displayName: "song1",
                groupID: groupID,
                groupName: "folder",
                groupRootPath: "/tmp/folder",
                status: .pending),
            Job(fileURL: URL(fileURLWithPath: "/tmp/folder/song2.wav"),
                displayName: "song2",
                groupID: groupID,
                groupName: "folder",
                groupRootPath: "/tmp/folder",
                status: .canceled,
                errorMessage: "Canceled by user")
        ]
        let view = JobQueueView(
            jobs: jobs,
            isEnqueuing: false,
            onReveal: { _ in },
            onPreviewRich: { _ in },
            onClear: {}
        )

        let stack = try view.inspect().vStack()
        XCTAssertTrue(try stack.findAll(ViewType.Text.self).contains { try $0.string() == "folder" })
    }

    func testHeaderShowsMixedStatePriority() throws {
        let view = JobQueueView(
            jobs: [
                makeJob(.failed),
                makeJob(.canceled),
                makeJob(.pending) // queued should win over failed/canceled
            ],
            isEnqueuing: false,
            onReveal: { _ in },
            onPreviewRich: { _ in },
            onClear: {}
        )
        let header = try view.inspect().vStack().hStack(0)
        XCTAssertNotNil(try header.find(text: "Queued"))
    }

    func testHeaderShowsCanceledBadge() throws {
        let view = JobQueueView(
            jobs: [makeJob(.canceled)],
            isEnqueuing: false,
            onReveal: { _ in },
            onPreviewRich: { _ in },
            onClear: {}
        )

        let header = try view.inspect().vStack().hStack(0)
        let badge = try header.find(text: "Canceled")
        XCTAssertEqual(try badge.string(), "Canceled")
    }

    func testCanceledRowShowsErrorMessage() throws {
        var canceled = makeJob(.canceled)
        canceled.errorMessage = "Canceled by user"
        let view = JobQueueView(
            jobs: [canceled],
            isEnqueuing: false,
            onReveal: { _ in },
            onPreviewRich: { _ in },
            onClear: {}
        )

        let rowText = try view.inspect().find(text: "Canceled by user")
        XCTAssertEqual(try rowText.string(), "Canceled by user")
    }
}
