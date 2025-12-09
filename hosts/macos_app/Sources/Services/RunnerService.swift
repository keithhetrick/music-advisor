import Foundation
import os

actor RunnerService {
    private let runner = CommandRunner()
    private let log = OSLog(subsystem: "com.bellweatherstudios.musicadvisor.macos", category: "runner.service")

    func run(command: [String], workingDirectory: String?, extraEnv: [String: String]) -> CommandResult {
        let signpost = Perf.begin(log, "runner.service.run")
        defer { Perf.end(log, "runner.service.run", signpost) }
        return runner.run(command: command, workingDirectory: workingDirectory, extraEnv: extraEnv)
    }
}
