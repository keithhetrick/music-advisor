import Foundation
import SwiftUI

@MainActor
final class CommandViewModel: ObservableObject {
    @Published var commandText: String
    @Published var workingDirectory: String
    @Published var envText: String
    @Published var status: String = ""
    @Published var stdout: String = ""
    @Published var stderr: String = ""
    @Published var exitCode: Int32 = 0
    @Published var isRunning: Bool = false
    @Published var parsedJSON: [String: AnyHashable] = [:]
    @Published var sidecarPath: String?
    @Published var summaryMetrics: [Metric] = []

    private let runner = CommandRunner()
    private let initialConfig: AppConfig

    init(config: AppConfig = .fromEnv()) {
        self.initialConfig = config
        self.commandText = config.command.joined(separator: " ")
        self.workingDirectory = config.workingDirectory ?? ""
        self.envText = config.extraEnv.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: "\n")
    }

    func loadDefaults() {
        let defaults = initialConfig
        commandText = defaults.command.joined(separator: " ")
        workingDirectory = defaults.workingDirectory ?? ""
        envText = defaults.extraEnv.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: "\n")
    }

    func setWorkingDirectory(_ path: String) {
        workingDirectory = path
    }

    func insertAudioPath(_ path: String) {
        var parts = splitCommand(commandText)
        if let idx = parts.firstIndex(of: "--audio"), parts.indices.contains(idx + 1) {
            parts[idx + 1] = shellEscape(path)
        } else {
            parts.append(contentsOf: ["--audio", shellEscape(path)])
        }
        commandText = parts.joined(separator: " ")
    }

    func run() {
        let parsedCommand = splitCommand(commandText)
        let env = parseEnv(envText)

        guard !parsedCommand.isEmpty else {
            status = "No command provided"
            return
        }

        sidecarPath = extractOutPath(from: parsedCommand)
        isRunning = true
        status = "Running..."
        stdout = ""
        stderr = ""
        summaryMetrics = []

        Task {
            let result = runner.run(command: parsedCommand,
                                    workingDirectory: workingDirectory.isEmpty ? nil : workingDirectory,
                                    extraEnv: env)
            stdout = result.stdout
            stderr = result.stderr
            exitCode = result.exitCode
            status = "Done (exit \(result.exitCode))"
            parsedJSON = parseJSON(result.stdout)
            summaryMetrics = extractMetrics(from: parsedJSON)
            isRunning = false
        }
    }

    // Basic shell-style splitter that respects single/double quotes and backslash escapes.
    private func splitCommand(_ text: String) -> [String] {
        var args: [String] = []
        var current = ""
        var inSingle = false
        var inDouble = false
        var isEscaping = false

        for ch in text {
            if isEscaping {
                current.append(ch)
                isEscaping = false
                continue
            }
            switch ch {
            case "\\":
                isEscaping = true
            case "\"" where !inSingle:
                inDouble.toggle()
            case "'" where !inDouble:
                inSingle.toggle()
            case " " where !inSingle && !inDouble,
                 "\t" where !inSingle && !inDouble,
                 "\n" where !inSingle && !inDouble:
                if !current.isEmpty {
                    args.append(current)
                    current = ""
                }
            default:
                current.append(ch)
            }
        }
        if !current.isEmpty { args.append(current) }
        return args
    }

    private func shellEscape(_ value: String) -> String {
        guard value.contains(where: { $0.isWhitespace }) else { return value }
        let escaped = value.replacingOccurrences(of: "\"", with: "\\\"")
        return "\"\(escaped)\""
    }

    private func parseEnv(_ text: String) -> [String: String] {
        var env: [String: String] = [:]
        let lines = text.split(separator: "\n")
        for line in lines {
            if let eq = line.firstIndex(of: "=") {
                let key = String(line[..<eq])
                let value = String(line[line.index(after: eq)...])
                env[key] = value
            }
        }
        return env
    }

    private func parseJSON(_ text: String) -> [String: AnyHashable] {
        guard let data = text.data(using: .utf8) else { return [:] }
        if let obj = try? JSONSerialization.jsonObject(with: data, options: []),
           let dict = obj as? [String: AnyHashable] {
            return dict
        }
        return [:]
    }

    private func extractOutPath(from args: [String]) -> String? {
        if let idx = args.firstIndex(of: "--out"), args.indices.contains(idx + 1) {
            return args[idx + 1].trimmingCharacters(in: .init(charactersIn: "\""))
        }
        return nil
    }

    private func extractMetrics(from dict: [String: AnyHashable]) -> [Metric] {
        func getDouble(_ key: String) -> Double? {
            dict[key] as? Double
        }
        func getString(_ key: String) -> String? {
            dict[key] as? String
        }
        var metrics: [Metric] = []
        if let tempo = getDouble("tempo_bpm") {
            metrics.append(Metric(label: "Tempo", value: String(format: "%.2f bpm", tempo)))
        }
        if let key = getString("key") {
            let mode = getString("mode") ?? ""
            metrics.append(Metric(label: "Key", value: "\(key) \(mode)".trimmingCharacters(in: .whitespaces)))
        }
        if let dur = getDouble("duration_sec") {
            metrics.append(Metric(label: "Duration", value: String(format: "%.1f s", dur)))
        }
        return metrics
    }
}

struct Metric: Identifiable, Hashable {
    let id = UUID()
    let label: String
    let value: String
}
