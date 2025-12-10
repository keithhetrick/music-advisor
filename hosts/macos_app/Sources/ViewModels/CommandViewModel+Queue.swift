import Foundation
import SwiftUI

@MainActor
final class JobQueueViewModel: ObservableObject {
    @Published private(set) var jobs: [Job] = []
    var jobsPublisher: Published<[Job]>.Publisher { $jobs }

    func addJobs(urls: [URL]) {
        let newJobs = urls.map { url in
            Job(fileURL: url, displayName: url.lastPathComponent)
        }
        jobs.append(contentsOf: newJobs)
    }

    func addPrecomputed(_ newJobs: [Job]) {
        jobs.append(contentsOf: newJobs)
    }

    func replaceAll(_ newJobs: [Job]) {
        jobs = newJobs
    }

    func clear() {
        jobs.removeAll()
    }

    func clearPending() {
        jobs.removeAll { $0.status == .pending }
    }

    func remove(jobID: UUID) {
        jobs.removeAll { $0.id == jobID && $0.status != .running }
    }

    func markRunning(jobID: UUID) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].status = .running
        }
    }

    func assignSidecar(jobID: UUID, sidecarPath: String) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].sidecarPath = sidecarPath
        }
    }

    func markDone(jobID: UUID, sidecarPath: String?) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            guard jobs[idx].status != .canceled else { return }
            jobs[idx].status = .done
            jobs[idx].sidecarPath = sidecarPath
        }
    }

    func cancelJob(jobID: UUID) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].status = .canceled
            jobs[idx].errorMessage = "Canceled by user"
        }
    }

    func cancelPending() {
        for idx in jobs.indices {
            if jobs[idx].status == .pending {
                jobs[idx].status = .canceled
                jobs[idx].errorMessage = "Canceled by user"
            }
        }
    }

    func clearCompleted() {
        jobs.removeAll { $0.status == .done }
    }

    func clearCanceledFailed() {
        jobs.removeAll { $0.status == .canceled || $0.status == .failed }
    }

    func markFailed(jobID: UUID, error: String?) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].status = .failed
            jobs[idx].errorMessage = error
        }
    }
}
