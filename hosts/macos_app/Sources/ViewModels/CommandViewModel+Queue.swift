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
            jobs[idx].status = .done
            jobs[idx].sidecarPath = sidecarPath
        }
    }

    func markFailed(jobID: UUID, error: String?) {
        if let idx = jobs.firstIndex(where: { $0.id == jobID }) {
            jobs[idx].status = .failed
            jobs[idx].errorMessage = error
        }
    }
}
