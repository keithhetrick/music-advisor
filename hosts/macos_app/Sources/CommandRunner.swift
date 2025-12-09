import Foundation
import os

struct CommandResult {
    let commandLine: String
    let stdout: String
    let stderr: String
    let exitCode: Int32
    let stdoutLines: [String]
    let stderrLines: [String]
    let spawnError: String?
}

struct CommandRunner {
    private let logPath = URL(fileURLWithPath: "/tmp/macos_app_cmd.log")

    func run(command: [String], workingDirectory: String?, extraEnv: [String: String]) -> CommandResult {
        guard let executable = command.first else {
            return CommandResult(commandLine: "", stdout: "", stderr: "No command provided", exitCode: -1, stdoutLines: [], stderrLines: [], spawnError: "No command provided")
        }

        let signpost = Perf.begin(Perf.runnerLog, "runner.exec")
        let args = Array(command.dropFirst())
        let process = Process()
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = args
        if let cwd = workingDirectory, !cwd.isEmpty {
            process.currentDirectoryURL = URL(fileURLWithPath: cwd)
        }

        var env = ProcessInfo.processInfo.environment
        extraEnv.forEach { env[$0.key] = $0.value }
        process.environment = env

        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe

        do {
            try process.run()
        } catch {
            let result = CommandResult(commandLine: command.joined(separator: " "),
                                       stdout: "",
                                       stderr: "Failed to start: \(error)",
                                       exitCode: -1,
                                       stdoutLines: [],
                                       stderrLines: [],
                                       spawnError: "\(error)")
            Perf.end(Perf.runnerLog, "runner.exec", signpost)
            return result
        }

        process.waitUntilExit()
        let stdoutData = outPipe.fileHandleForReading.readDataToEndOfFile()
        let stderrData = errPipe.fileHandleForReading.readDataToEndOfFile()

        let result = CommandResult(
            commandLine: ([executable] + args).joined(separator: " "),
            stdout: String(data: stdoutData, encoding: .utf8) ?? "",
            stderr: String(data: stderrData, encoding: .utf8) ?? "",
            exitCode: process.terminationStatus,
            stdoutLines: (String(data: stdoutData, encoding: .utf8) ?? "").components(separatedBy: .newlines),
            stderrLines: (String(data: stderrData, encoding: .utf8) ?? "").components(separatedBy: .newlines),
            spawnError: nil
        )

        // Write a simple log for debugging runs.
        let log = """
        === macos_app run ===
        cwd: \(workingDirectory ?? "(nil)")
        env extras: \(extraEnv)
        command: \(result.commandLine)
        exit: \(result.exitCode)
        --- stdout ---
        \(result.stdout)
        --- stderr ---
        \(result.stderr)
        =====================

        """
        try? log.write(to: logPath, atomically: false, encoding: .utf8)
        Perf.end(Perf.runnerLog, "runner.exec", signpost)

        return result
    }
}
