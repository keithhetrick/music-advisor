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

    func run() {
        let parsedCommand = splitCommand(commandText)
        let env = parseEnv(envText)

        guard !parsedCommand.isEmpty else {
            status = "No command provided"
            return
        }

        isRunning = true
        status = "Running..."
        stdout = ""
        stderr = ""

        Task {
            let result = runner.run(command: parsedCommand,
                                    workingDirectory: workingDirectory.isEmpty ? nil : workingDirectory,
                                    extraEnv: env)
            stdout = result.stdout
            stderr = result.stderr
            exitCode = result.exitCode
            status = "Done (exit \(result.exitCode))"
            parsedJSON = parseJSON(result.stdout)
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
            case " ", "\t", "\n" where !inSingle && !inDouble:
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
}
