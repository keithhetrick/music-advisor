import XCTest
@testable import MusicAdvisorMacApp

@MainActor
final class UITestSupportQueueControllerTests: XCTestCase {
    func testSeedCreatesJobsWithExpectedStatuses() {
        let controller = UITestQueueController(root: UITestSupport.tempRoot)
        XCTAssertEqual(controller.jobs.count, 4)
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .running }))
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .pending }))
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .done }))
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .canceled }))
    }

    func testStartStopResumeAndClear() {
        let controller = UITestQueueController(root: UITestSupport.tempRoot)

        controller.start()
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .running }), "start should promote a pending job to running")

        controller.stop()
        XCTAssertFalse(controller.jobs.contains(where: { $0.status == .running }))
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .canceled }))

        controller.resumeCanceled()
        XCTAssertFalse(controller.jobs.contains(where: { $0.status == .canceled }))
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .pending }))

        controller.cancelPending()
        XCTAssertFalse(controller.jobs.contains(where: { $0.status == .pending }))
        XCTAssertTrue(controller.jobs.contains(where: { $0.status == .canceled }))

        controller.clearAll()
        XCTAssertEqual(controller.jobs.count, 0)
    }

    func testMarkPendingAsCanceledUpdatesState() {
        let controller = UITestQueueController(root: UITestSupport.tempRoot)
        controller.markPendingAsCanceled()
        XCTAssertFalse(controller.jobs.contains { $0.status == .pending })
        XCTAssertTrue(controller.jobs.contains { $0.status == .canceled })
    }

    func testClearCompletedAndCanceled() {
        let controller = UITestQueueController(root: UITestSupport.tempRoot)
        controller.clearCompleted()
        XCTAssertFalse(controller.jobs.contains { $0.status == .done })

        controller.clearCanceledFailed()
        XCTAssertFalse(controller.jobs.contains { $0.status == .canceled })
    }
}
