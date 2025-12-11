import XCTest
@testable import MAQueue

@MainActor
final class JobQueueViewModelTests: XCTestCase {
    private func makeJob(name: String = "file.wav",
                         status: Job.Status = .pending,
                         groupID: UUID? = nil,
                         groupName: String? = nil,
                         groupRootPath: String? = nil) -> Job {
        Job(fileURL: URL(fileURLWithPath: "/tmp/\(name)"),
            displayName: name,
            groupID: groupID,
            groupName: groupName,
            groupRootPath: groupRootPath,
            status: status)
    }

    func testCancelPendingMarksAllAndPreservesOrder() {
        let vm = JobQueueViewModel()
        let first = makeJob(name: "a.wav", status: .pending)
        let second = makeJob(name: "b.wav", status: .pending)
        vm.addPrecomputed([first, second])

        vm.cancelPending()

        XCTAssertEqual(vm.jobs.count, 2)
        XCTAssertEqual(vm.jobs[0].status, .canceled)
        XCTAssertEqual(vm.jobs[1].status, .canceled)
        XCTAssertEqual(vm.jobs[0].errorMessage, "Canceled by user")
    }

    func testCancelJobMarksFinishedWithMessage() {
        let vm = JobQueueViewModel()
        let job = makeJob(name: "run.wav", status: .running)
        vm.addPrecomputed([job])

        vm.cancelJob(jobID: job.id)

        XCTAssertEqual(vm.jobs.first?.status, .canceled)
        XCTAssertEqual(vm.jobs.first?.errorMessage, "Canceled by user")
        XCTAssertNotNil(vm.jobs.first?.finishedAt)
    }

    func testClearCompletedOnlyRemovesDone() {
        let vm = JobQueueViewModel()
        let done = makeJob(name: "done.wav", status: .done)
        let pending = makeJob(name: "pending.wav", status: .pending)
        vm.addPrecomputed([done, pending])

        vm.clearCompleted()

        XCTAssertEqual(vm.jobs.map(\.status), [.pending])
    }

    func testClearCanceledFailedRemovesOnlyFailedAndCanceled() {
        let vm = JobQueueViewModel()
        let failed = makeJob(name: "bad.wav", status: .failed)
        let canceled = makeJob(name: "stop.wav", status: .canceled)
        let pending = makeJob(name: "pending.wav", status: .pending)
        vm.addPrecomputed([failed, canceled, pending])

        vm.clearCanceledFailed()

        XCTAssertEqual(vm.jobs.count, 1)
        XCTAssertEqual(vm.jobs.first?.status, .pending)
    }

    func testResumeCanceledResetsState() {
        let vm = JobQueueViewModel()
        var canceled = makeJob(name: "stop.wav", status: .canceled)
        canceled.errorMessage = "Canceled by user"
        canceled.startedAt = Date().addingTimeInterval(-10)
        canceled.finishedAt = Date()
        canceled.attempts = 1
        vm.addPrecomputed([canceled])

        vm.resumeCanceled()

        XCTAssertEqual(vm.jobs.first?.status, .pending)
        XCTAssertNil(vm.jobs.first?.errorMessage)
        XCTAssertNil(vm.jobs.first?.startedAt)
        XCTAssertNil(vm.jobs.first?.finishedAt)
        XCTAssertEqual(vm.jobs.first?.attempts, 0)
    }

    func testMarkDoneDoesNotOverrideCanceled() {
        let vm = JobQueueViewModel()
        let canceled = makeJob(name: "stop.wav", status: .canceled)
        vm.addPrecomputed([canceled])

        vm.markDone(jobID: canceled.id, sidecarPath: "/tmp/out.json")

        XCTAssertEqual(vm.jobs.first?.status, .canceled)
        XCTAssertNil(vm.jobs.first?.sidecarPath)
    }

    func testRemoveSkipsRunningJob() {
        let vm = JobQueueViewModel()
        let running = makeJob(name: "run.wav", status: .running)
        let pending = makeJob(name: "pending.wav", status: .pending)
        vm.addPrecomputed([running, pending])

        vm.remove(jobID: running.id)
        vm.remove(jobID: pending.id)

        XCTAssertEqual(vm.jobs.count, 1)
        XCTAssertEqual(vm.jobs.first?.status, .running)
    }
}
