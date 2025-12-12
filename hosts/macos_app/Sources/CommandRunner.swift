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
    /// Optional watchdog; nil disables forced termination. Configurable via MA_APP_RUN_TIMEOUT (seconds).
    private let timeoutSeconds: TimeInterval?

    init(timeoutSeconds: TimeInterval? = {
        // Default to 10 minutes to prevent infinite hangs; override with MA_APP_RUN_TIMEOUT or set to "0" to disable.
        if let raw = ProcessInfo.processInfo.environment["MA_APP_RUN_TIMEOUT"] {
            if raw == "0" { return nil }
            if let value = TimeInterval(raw) { return value }
        }
        return 600
    }()) {
        self.timeoutSeconds = timeoutSeconds
    }

    func run(command: [String], workingDirectory: String?, extraEnv: [String: String], onSpawn: ((Process) -> Void)? = nil) -> CommandResult {
        guard let executable = command.first else {
            return CommandResult(commandLine: "", stdout: "", stderr: "No command provided", exitCode: -1, stdoutLines: [], stderrLines: [], spawnError: "No command provided")
        }

        let signpost = Perf.begin(Perf.runnerLog, "runner.exec")
        let args = Array(command.dropFirst())
        let process = Process()
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = args
        // Ensure we always run from a real working directory.
        let effectiveCwd = (workingDirectory?.isEmpty == false) ? workingDirectory! : FileManager.default.currentDirectoryPath
        process.currentDirectoryURL = URL(fileURLWithPath: effectiveCwd)

        var env = ProcessInfo.processInfo.environment
        // Merge caller-provided env on top of process env.
        extraEnv.forEach { env[$0.key] = $0.value }

        // Normalize HOME and REPO so downstream scripts see stable paths.
        if env["HOME"] == nil {
            env["HOME"] = NSHomeDirectory()
        }
        if env["REPO"] == nil {
            env["REPO"] = effectiveCwd
        }

        // Ensure PYTHONPATH is present and points at the repo root when possible.
        if env["PYTHONPATH"] == nil {
            let cwdURL = URL(fileURLWithPath: effectiveCwd)
            if cwdURL.pathComponents.suffix(2) == ["hosts", "macos_app"] {
                env["PYTHONPATH"] = cwdURL.deletingLastPathComponent().deletingLastPathComponent().path
            } else {
                env["PYTHONPATH"] = cwdURL.path
            }
        }

        // Stabilize PATH: prepend venv/bin and common locations while keeping the user PATH.
        let repo = env["REPO"] ?? effectiveCwd
        var pathParts: [String] = []
        let venvBin = "\(repo)/.venv/bin"
        if FileManager.default.fileExists(atPath: venvBin) {
            pathParts.append(venvBin)
        }
        pathParts.append(contentsOf: ["/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
        if let existing = env["PATH"] {
            pathParts.append(existing)
        }
        env["PATH"] = pathParts.joined(separator: ":")

        process.environment = env

        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe

        // Optional watchdog to prevent hangs; disabled when timeoutSeconds is nil.
        var timedOut = false
        var killItem: DispatchWorkItem?
        if let timeoutSeconds {
            let item = DispatchWorkItem { [process] in
                if process.isRunning {
                    timedOut = true
                    process.terminate()
                }
            }
            killItem = item
            DispatchQueue.global().asyncAfter(deadline: .now() + timeoutSeconds, execute: item)
        }

        do {
            onSpawn?(process)
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
        killItem?.cancel()
        let stdoutData = outPipe.fileHandleForReading.readDataToEndOfFile()
        let stderrData = errPipe.fileHandleForReading.readDataToEndOfFile()

        let timeoutSuffix: String
        if timedOut, let timeoutSeconds {
            timeoutSuffix = "Timed out after \(Int(timeoutSeconds))s; process terminated.\n"
        } else if timedOut {
            timeoutSuffix = "Timed out; process terminated.\n"
        } else {
            timeoutSuffix = ""
        }

        let result = CommandResult(
            commandLine: ([executable] + args).joined(separator: " "),
            stdout: String(data: stdoutData, encoding: .utf8) ?? "",
            stderr: timeoutSuffix + (String(data: stderrData, encoding: .utf8) ?? ""),
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
