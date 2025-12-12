import Foundation
import os

actor RunnerService {
    private let runner: CommandRunner
    private let log = OSLog(subsystem: "com.bellweatherstudios.musicadvisor.macos", category: "runner.service")
    private let baseWorkingDirectory: String?
    private let baseEnv: [String: String]
    private var currentProcess: Process?

    // Lightweight wrapper to allow moving Process across concurrency domains.
    private struct ProcessBox: @unchecked Sendable {
        let process: Process
    }

    init(config: AppConfig = .fromEnv()) {
        self.baseWorkingDirectory = config.workingDirectory
        self.baseEnv = config.extraEnv
        self.runner = CommandRunner()
    }

    func run(command: [String], workingDirectory: String?, extraEnv: [String: String]) async -> CommandResult {
        let signpost = Perf.begin(log, "runner.service.run")
        defer { Perf.end(log, "runner.service.run", signpost) }
        let cwd = (workingDirectory?.isEmpty == false) ? workingDirectory : baseWorkingDirectory
        let mergedEnv = baseEnv.merging(extraEnv) { _, new in new }
        var boxed: ProcessBox?
        let result = runner.run(command: command,
                                workingDirectory: cwd,
                                extraEnv: mergedEnv,
                                onSpawn: { process in
                                    boxed = ProcessBox(process: process)
                                })
        if let boxed {
            // Updating actor state from actor context.
            setCurrent(boxed.process)
        }
        clearCurrent()
        return result
    }

    func cancelRunningProcess() async {
        if let process = currentProcess {
            let box = ProcessBox(process: process)
            if box.process.isRunning {
                box.process.terminate()
            }
            // If it is still hanging, escalate to a hard kill after a short delay.
            Task.detached { [box, weak self] in
                try? await Task.sleep(nanoseconds: 500_000_000)
                if box.process.isRunning {
                    box.process.interrupt()
                    box.process.terminate()
                }
                await self?.clearCurrent()
            }
        }
        clearCurrent()
    }

    private func setCurrent(_ process: Process) {
        currentProcess = process
    }

    private func clearCurrent() {
        currentProcess = nil
    }
}
