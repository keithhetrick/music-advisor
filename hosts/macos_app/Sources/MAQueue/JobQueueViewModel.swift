import Foundation
import Combine

@MainActor
public final class JobQueueViewModel: ObservableObject {
    @Published public private(set) var jobs: [Job] = []
    public var jobsPublisher: Published<[Job]>.Publisher { $jobs }

    public init() {}

    public func addJobs(urls: [URL]) {
        let newJobs = urls.map { url in
            Job(fileURL: url, displayName: url.lastPathComponent)
        }
        jobs.append(contentsOf: newJobs)
        QueueLogger.shared.log(.debug, "addJobs count=\(newJobs.count)")
    }

    public func addPrecomputed(_ newJobs: [Job]) {
        jobs.append(contentsOf: newJobs)
        QueueLogger.shared.log(.debug, "addPrecomputed count=\(newJobs.count)")
    }

    public func replaceAll(_ newJobs: [Job]) {
        jobs = newJobs
        QueueLogger.shared.log(.debug, "replaceAll count=\(newJobs.count)")
    }

    public func clear() {
        jobs.removeAll()
        QueueLogger.shared.log(.debug, "clear all")
    }

    public func clearPending() {
        jobs.removeAll { $0.status == .pending }
        QueueLogger.shared.log(.debug, "clear pending")
    }

    public func remove(jobID: UUID) {
        jobs.removeAll { $0.id == jobID && $0.status != .running }
        QueueLogger.shared.log(.debug, "remove job \(jobID)")
    }

    public func markRunning(jobID: UUID) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].status = .running
            jobs[idx].startedAt = Date()
            jobs[idx].updatedAt = Date()
            jobs[idx].attempts += 1
            QueueLogger.shared.log(.debug, "markRunning \(jobID)")
        }
    }

    public func assignSidecar(jobID: UUID, sidecarPath: String) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].sidecarPath = sidecarPath
            jobs[idx].updatedAt = Date()
            QueueLogger.shared.log(.debug, "assignSidecar \(jobID) path=\(sidecarPath)")
        }
    }

    public func markDone(jobID: UUID, sidecarPath: String?) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            guard jobs[idx].status != .canceled else { return }
            jobs[idx].status = .done
            jobs[idx].sidecarPath = sidecarPath
            jobs[idx].updatedAt = Date()
            jobs[idx].finishedAt = Date()
            QueueLogger.shared.log(.debug, "markDone \(jobID)")
        }
    }

    public func cancelJob(jobID: UUID) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].status = .canceled
            jobs[idx].errorMessage = "Canceled by user"
            jobs[idx].updatedAt = Date()
            jobs[idx].finishedAt = Date()
            QueueLogger.shared.log(.debug, "cancelJob \(jobID)")
        }
    }

    public func cancelPending() {
        for idx in jobs.indices {
            if jobs[idx].status == .pending {
                jobs[idx].status = .canceled
                jobs[idx].errorMessage = "Canceled by user"
                jobs[idx].updatedAt = Date()
                jobs[idx].finishedAt = Date()
            }
        }
        QueueLogger.shared.log(.debug, "cancelPending")
    }

    public func clearCompleted() {
        jobs.removeAll { $0.status == .done }
        QueueLogger.shared.log(.debug, "clearCompleted")
    }

    public func clearCanceledFailed() {
        jobs.removeAll { $0.status == .canceled || $0.status == .failed }
        QueueLogger.shared.log(.debug, "clearCanceledFailed")
    }

    public func resumeCanceled() {
        var resumed = 0
        for idx in jobs.indices {
            if jobs[idx].status == .canceled {
                jobs[idx].status = .pending
                jobs[idx].errorMessage = nil
                jobs[idx].updatedAt = Date()
                jobs[idx].startedAt = nil
                jobs[idx].finishedAt = nil
                jobs[idx].attempts = 0
                resumed += 1
            }
        }
        if resumed > 0 {
            QueueLogger.shared.log(.debug, "resumeCanceled count=\(resumed)")
        }
    }

    public func markFailed(jobID: UUID, error: String?) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }),
           jobs[idx].status != .canceled {
            jobs[idx].status = .failed
            jobs[idx].errorMessage = error
            jobs[idx].updatedAt = Date()
            jobs[idx].finishedAt = Date()
            let errText = error ?? ""
            QueueLogger.shared.log(.error, "markFailed \(jobID) err=\(errText)")
        }
    }
}
