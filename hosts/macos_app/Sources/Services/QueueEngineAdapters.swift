import Foundation
import MAQueue

struct CommandRunnerAdapter: QueueRunner, QueueRunnerCancelable {
    let runner: RunnerService

    func run(job: Job) async -> QueueRunResult {
        let command = job.preparedCommand ?? []
        guard !command.isEmpty else {
            return QueueRunResult(exitCode: -1, stdout: "", stderr: "No command", spawnError: "No command")
        }
        let result = await runner.run(command: command, workingDirectory: nil, extraEnv: [:])
        return QueueRunResult(exitCode: result.exitCode,
                              stdout: result.stdout,
                              stderr: result.stderr,
                              spawnError: result.spawnError)
    }

    func cancelRunning() async {
        await runner.cancelRunningProcess()
    }
}

struct SidecarResolverAdapter: SidecarResolver {
    func ensureSidecar(for job: Job) -> (final: String, temp: String) {
        let finalPath = job.preparedOutPath ?? defaultSidecar(for: job.fileURL)
        ensureDir(path: finalPath)
        let temp = finalPath + ".tmp-\(UUID().uuidString)"
        return (finalPath, temp)
    }

    func cleanupTemp(path: String?) {
        if let path, FileManager.default.fileExists(atPath: path) {
            try? FileManager.default.removeItem(atPath: path)
        }
    }

    func finalize(tempPath: String?, finalPath: String?) {
        let fm = FileManager.default
        guard let finalPath else { return }
        ensureDir(path: finalPath)
        if fm.fileExists(atPath: finalPath) {
            if let temp = tempPath, fm.fileExists(atPath: temp) {
                try? fm.removeItem(atPath: temp)
            }
            return
        }
        guard let tempPath else { return }
        guard fm.fileExists(atPath: tempPath) else { return }
        if fm.fileExists(atPath: finalPath) {
            try? fm.removeItem(atPath: tempPath)
            return
        }
        try? fm.moveItem(atPath: tempPath, toPath: finalPath)
    }

    private func defaultSidecar(for audioURL: URL) -> String {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let sidecarDir = appDir.appendingPathComponent("sidecars", isDirectory: true)
        try? FileManager.default.createDirectory(at: sidecarDir, withIntermediateDirectories: true)
        let base = audioURL.deletingPathExtension().lastPathComponent
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let filename = "\(base)_\(timestamp).json"
        return sidecarDir.appendingPathComponent(filename).path
    }

    private func ensureDir(path: String) {
        let dir = URL(fileURLWithPath: path).deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    }
}

final class TrackVMIngestSink: IngestSink {
    weak var trackVM: TrackListViewModel?

    init(trackVM: TrackListViewModel) {
        self.trackVM = trackVM
    }

    func ingest(fileURL: URL, jobID: UUID?) async -> Bool {
        guard let vm = trackVM else { return false }
        await MainActor.run {
            vm.ingestDropped(urls: [fileURL])
        }
        return true
    }
}
