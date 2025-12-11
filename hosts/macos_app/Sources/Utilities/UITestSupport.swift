import Foundation
import MAQueue

enum UITestSupport {
    static let isEnabled = ProcessInfo.processInfo.environment["MA_UI_TEST_MODE"] == "1"

    static var tempRoot: URL {
        let base = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        return base.appendingPathComponent("MusicAdvisorMacApp-UITests", isDirectory: true)
    }

    @MainActor
    static func makeQueueController() -> UITestQueueController {
        UITestQueueController(root: tempRoot)
    }

    static func sampleJob(name: String) -> Job {
        let url = tempRoot.appendingPathComponent("audio", isDirectory: true).appendingPathComponent(name)
        let now = Date()
        return Job(fileURL: url,
                   displayName: name,
                   status: .pending,
                   createdAt: now,
                   updatedAt: now)
    }
}

@MainActor
final class UITestQueueController: ObservableObject {
    @Published private(set) var jobs: [Job] = []
    private let root: URL
    private var task: Task<Void, Never>?

    init(root: URL) {
        self.root = root
        seed()
    }

    func seed() {
        task?.cancel()
        let audioRoot = root.appendingPathComponent("audio", isDirectory: true)
        try? FileManager.default.createDirectory(at: audioRoot, withIntermediateDirectories: true)
        let folderRoot = audioRoot.appendingPathComponent("AlbumA", isDirectory: true)
        try? FileManager.default.createDirectory(at: folderRoot, withIntermediateDirectories: true)

        let groupedID = UUID()
        let now = Date()
        jobs = [
            Job(fileURL: folderRoot.appendingPathComponent("track_one.wav"),
                displayName: "track_one.wav",
                groupID: groupedID,
                groupName: "AlbumA",
                groupRootPath: folderRoot.path,
                status: .running,
                createdAt: now,
                updatedAt: now,
                startedAt: now.addingTimeInterval(-1)),
            Job(fileURL: folderRoot.appendingPathComponent("track_two.wav"),
                displayName: "track_two.wav",
                groupID: groupedID,
                groupName: "AlbumA",
                groupRootPath: folderRoot.path,
                status: .pending,
                createdAt: now,
                updatedAt: now),
            Job(fileURL: audioRoot.appendingPathComponent("solo_take.flac"),
                displayName: "solo_take.flac",
                status: .done,
                sidecarPath: audioRoot.appendingPathComponent("solo_take.json").path,
                createdAt: now.addingTimeInterval(-5),
                updatedAt: now.addingTimeInterval(-2),
                finishedAt: now.addingTimeInterval(-2)),
            Job(fileURL: audioRoot.appendingPathComponent("scratch.aiff"),
                displayName: "scratch.aiff",
                status: .canceled,
                errorMessage: "Canceled by user",
                createdAt: now.addingTimeInterval(-10),
                updatedAt: now.addingTimeInterval(-5),
                finishedAt: now.addingTimeInterval(-5))
        ]
    }

    func enqueue(_ newJobs: [Job]) {
        jobs.append(contentsOf: newJobs)
    }

    func start() {
        task?.cancel()
        guard let idx = jobs.firstIndex(where: { $0.status == .pending }) else { return }
        jobs[idx].status = .running
        jobs[idx].startedAt = Date()
        jobs[idx].updatedAt = Date()
        task = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 400_000_000)
            self?.finishRunningJob()
        }
    }

    func stop() {
        task?.cancel()
        for index in jobs.indices {
            if jobs[index].status == .running || jobs[index].status == .pending {
                jobs[index].status = .canceled
                jobs[index].errorMessage = "Canceled by user"
                jobs[index].finishedAt = Date()
                jobs[index].updatedAt = Date()
            }
        }
    }

    func cancelPending() {
        for index in jobs.indices where jobs[index].status == .pending {
            jobs[index].status = .canceled
            jobs[index].errorMessage = "Canceled by user"
            jobs[index].finishedAt = Date()
            jobs[index].updatedAt = Date()
        }
    }

    func resumeCanceled() {
        let now = Date()
        for index in jobs.indices where jobs[index].status == .canceled {
            jobs[index].status = .pending
            jobs[index].errorMessage = nil
            jobs[index].startedAt = nil
            jobs[index].finishedAt = nil
            jobs[index].updatedAt = now
        }
    }

    func clearAll() {
        task?.cancel()
        jobs.removeAll()
    }

    func clearCompleted() {
        jobs.removeAll { $0.status == .done }
    }

    func clearCanceledFailed() {
        jobs.removeAll { $0.status == .canceled || $0.status == .failed }
    }

    func remove(_ id: UUID) {
        jobs.removeAll { $0.id == id }
    }

    func markPendingAsCanceled() {
        for index in jobs.indices where jobs[index].status == .pending {
            jobs[index].status = .canceled
            jobs[index].errorMessage = "Canceled by user"
            jobs[index].finishedAt = Date()
            jobs[index].updatedAt = Date()
        }
    }

    func ensureResumeAvailable() {
        markPendingAsCanceled()
    }

    func forceResumeAndStart() {
        resumeCanceled()
        start()
    }

    func expandAllFolders() {
        // No-op here; folder expansion is handled in UI-level state. This hook exists for parity.
    }

    private func finishRunningJob() {
        guard let idx = jobs.firstIndex(where: { $0.status == .running }) else { return }
        jobs[idx].status = .done
        jobs[idx].finishedAt = Date()
        jobs[idx].updatedAt = Date()
        if jobs.contains(where: { $0.status == .pending }) {
            start()
        }
    }
}
