import XCTest
@testable import MAQueue
@testable import MusicAdvisorMacApp

@MainActor
final class JobQueueViewTests: XCTestCase {
    private func job(_ status: Job.Status) -> Job {
        Job(fileURL: URL(fileURLWithPath: "/tmp/a.wav"), displayName: "a", status: status)
    }

    func testHeaderStatusPriorityOrder() {
        XCTAssertEqual(JobQueueView.headerStatus(for: []), .empty)
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.pending)]), .queued)
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.done)]), .done)
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.canceled)]), .canceled)
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.failed)]), .failed)
        // running should take precedence even if other statuses exist
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.running), job(.failed)]), .processing)
    }

    func testResumeCanceledVisibility() {
        XCTAssertFalse(JobQueueView.shouldShowResumeCanceled(for: []))
        XCTAssertTrue(JobQueueView.shouldShowResumeCanceled(for: [job(.canceled)]))
        XCTAssertTrue(JobQueueView.shouldShowResumeCanceled(for: [job(.pending), job(.canceled)]))
    }

    func testHeaderStatusPriorityWithMixedStates() {
        // queued takes precedence over failed/canceled/done when none running
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.pending), job(.failed), job(.canceled)]), .queued)
        // failed takes precedence over canceled/done when no pending/running
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.failed), job(.canceled)]), .failed)
        // canceled takes precedence over done when no pending/running/failed
        XCTAssertEqual(JobQueueView.headerStatus(for: [job(.canceled), job(.done)]), .canceled)
    }

    func testButtonVisibilityHelpers() {
        XCTAssertTrue(JobQueueView.shouldShowStop(onStop: {}))
        XCTAssertFalse(JobQueueView.shouldShowStop(onStop: nil))

        XCTAssertTrue(JobQueueView.shouldShowCancelPending(onCancelPending: {}))
        XCTAssertFalse(JobQueueView.shouldShowCancelPending(onCancelPending: nil))

        XCTAssertTrue(JobQueueView.shouldShowClearCompleted(onClearCompleted: {}))
        XCTAssertFalse(JobQueueView.shouldShowClearCompleted(onClearCompleted: nil))

        XCTAssertTrue(JobQueueView.shouldShowClearCanceledFailed(onClearCanceledFailed: {}))
        XCTAssertFalse(JobQueueView.shouldShowClearCanceledFailed(onClearCanceledFailed: nil))
    }
}
