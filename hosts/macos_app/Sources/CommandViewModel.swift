import Foundation
import SwiftUI
import MAStyle
import Combine

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
    @Published var lastRunTime: Date?
    @Published var lastDuration: TimeInterval?
    @Published var sidecarPreview: String = ""
    @Published var profiles: [AppConfig.Profile] = []
    @Published var selectedProfile: String = ""
    @Published var queueVM = JobQueueViewModel()
    @Published var currentJobID: UUID?

    private let runner = CommandRunner()
    private let initialConfig: AppConfig

    init(config: AppConfig = .fromEnv()) {
        self.initialConfig = config
        self.commandText = config.command.joined(separator: " ")
        self.workingDirectory = config.workingDirectory ?? ""
        self.envText = config.extraEnv.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: "\n")
        self.profiles = config.profiles
        // Default to a sensible profile if present.
        if let pipelineProfile = config.profiles.first(where: { $0.name.lowercased().contains("pipeline") }) {
            self.selectedProfile = pipelineProfile.name
            self.commandText = pipelineProfile.command.joined(separator: " ")
            self.workingDirectory = pipelineProfile.workingDirectory ?? self.workingDirectory
            let mergedEnv = pipelineProfile.extraEnv.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: "\n")
            self.envText = mergedEnv.isEmpty ? self.envText : mergedEnv
            if let out = pipelineProfile.outputPath {
                self.sidecarPath = out
            }
        } else {
            self.selectedProfile = config.profiles.first?.name ?? ""
            if let firstProfile = config.profiles.first, let out = firstProfile.outputPath {
                self.sidecarPath = out
            }
        }
    }

    func loadDefaults() {
        let defaults = initialConfig
        commandText = defaults.command.joined(separator: " ")
        workingDirectory = defaults.workingDirectory ?? ""
        envText = defaults.extraEnv.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: "\n")
        profiles = defaults.profiles
        selectedProfile = defaults.profiles.first?.name ?? ""
        if let out = defaults.profiles.first?.outputPath {
            sidecarPath = out
        }
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

    func applySelectedProfile() {
        guard let profile = profiles.first(where: { $0.name == selectedProfile }) else { return }
        commandText = profile.command.joined(separator: " ")
        workingDirectory = profile.workingDirectory ?? ""
        let mergedEnv = profile.extraEnv.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: "\n")
        envText = mergedEnv
        if let out = profile.outputPath {
            sidecarPath = out
        }
    }

    func reloadConfig() {
        let refreshed = AppConfig.fromEnv()
        commandText = refreshed.command.joined(separator: " ")
        workingDirectory = refreshed.workingDirectory ?? ""
        envText = refreshed.extraEnv.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: "\n")
        profiles = refreshed.profiles
        selectedProfile = refreshed.profiles.first?.name ?? ""
        if let out = refreshed.profiles.first?.outputPath {
            sidecarPath = out
        }
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
        lastDuration = nil
        sidecarPreview = ""

        Task.detached {
            let start = Date()
            let result = await self.runner.run(command: parsedCommand,
                                               workingDirectory: self.workingDirectory.isEmpty ? nil : self.workingDirectory,
                                               extraEnv: env)
            let duration = Date().timeIntervalSince(start)
            // Parse heavy-ish work off the main actor.
            let parsed = await self.parseJSON(result.stdout)
            let metrics = await self.extractMetrics(from: parsed)

            await MainActor.run {
                self.lastDuration = duration
                self.stdout = result.stdout
                self.stderr = result.stderr
                self.exitCode = result.exitCode
                self.status = "Done (exit \(result.exitCode))"
                self.parsedJSON = parsed
                self.summaryMetrics = metrics
                self.lastRunTime = Date()
                self.isRunning = false

                if let jobID = self.currentJobID {
                    if result.exitCode == 0 {
                        self.queueVM.markDone(jobID: jobID, sidecarPath: self.sidecarPath)
                    } else {
                        let err = self.stderr.isEmpty ? self.status : self.stderr
                        self.queueVM.markFailed(jobID: jobID, error: err)
                    }
                    self.currentJobID = nil
                    self.processNextJobIfNeeded()
                }
            }
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
        if let lufs = getDouble("loudness_integrated_lufs") {
            metrics.append(Metric(label: "LUFS", value: String(format: "%.1f LUFS", lufs)))
        }
        if let peak = getDouble("peak_db") {
            metrics.append(Metric(label: "Peak", value: String(format: "%.1f dB", peak)))
        }
        if let crest = getDouble("crest_factor_db") {
            metrics.append(Metric(label: "Crest", value: String(format: "%.1f dB", crest)))
        }
        return metrics
    }

    func runSmoke() {
        let env = parseEnv(envText)
        let base = workingDirectory.isEmpty ? (initialConfig.workingDirectory ?? FileManager.default.currentDirectoryPath) : workingDirectory
        let scriptPath = "\(base)/hosts/macos_app/scripts/smoke_default.sh"

        isRunning = true
        status = "Running smoke..."
        stdout = ""
        stderr = ""
        summaryMetrics = []
        lastDuration = nil
        sidecarPreview = ""

        Task {
            let start = Date()
            let result = runner.run(command: ["/bin/zsh", scriptPath],
                                    workingDirectory: base,
                                    extraEnv: env)
            lastDuration = Date().timeIntervalSince(start)
            stdout = result.stdout
            stderr = result.stderr
            exitCode = result.exitCode
            status = "Smoke done (exit \(result.exitCode))"
            parsedJSON = [:]
            sidecarPath = "/tmp/ma_features.json"
            lastRunTime = Date()
            isRunning = false
            if let jobID = currentJobID {
                if result.exitCode == 0 {
                    queueVM.markDone(jobID: jobID, sidecarPath: sidecarPath)
                } else {
                    let err = stderr.isEmpty ? status : stderr
                    queueVM.markFailed(jobID: jobID, error: err)
                }
                currentJobID = nil
                processNextJobIfNeeded()
            }
        }
    }

    func loadSidecarPreview() {
        guard let path = sidecarPath else {
            sidecarPreview = "(no sidecar path)"
            return
        }
        let url = URL(fileURLWithPath: path)
        guard let data = try? Data(contentsOf: url) else {
            sidecarPreview = "(sidecar not found)"
            return
        }
        if let obj = try? JSONSerialization.jsonObject(with: data, options: []),
           let dict = obj as? [String: Any] {
            let limited = limitedDict(dict, maxItems: 12)
            if let previewData = try? JSONSerialization.data(withJSONObject: limited, options: [.prettyPrinted]),
               let previewString = String(data: previewData, encoding: .utf8) {
                sidecarPreview = previewString
                return
            }
        }
        if let text = String(data: data, encoding: .utf8) {
            sidecarPreview = text
        } else {
            sidecarPreview = "(sidecar unreadable)"
        }
    }

    private func limitedDict(_ dict: [String: Any], maxItems: Int) -> [String: Any] {
        let keys = Array(dict.keys).sorted().prefix(maxItems)
        var result: [String: Any] = [:]
        for k in keys {
            result[k] = dict[k]
        }
        return result
    }

    // MARK: - Queue
    func enqueue(files: [URL]) {
        queueVM.addJobs(urls: files)
        processNextJobIfNeeded()
    }

    private func processNextJobIfNeeded() {
        guard !isRunning else { return }
        guard let next = queueVM.jobs.first(where: { $0.status == .pending }) else { return }
        currentJobID = next.id

        let sidecarPathForJob = makeSidecarPath(for: next.fileURL)

        // Replace --audio with the next file
        var parts = splitCommand(commandText)
        if let idx = parts.firstIndex(of: "--audio"), parts.indices.contains(idx + 1) {
            parts[idx + 1] = shellEscape(next.fileURL.path)
        } else {
            parts.append(contentsOf: ["--audio", shellEscape(next.fileURL.path)])
        }
        if let outIdx = parts.firstIndex(of: "--out"), parts.indices.contains(outIdx + 1) {
            parts[outIdx + 1] = shellEscape(sidecarPathForJob)
        } else {
            parts.append(contentsOf: ["--out", shellEscape(sidecarPathForJob)])
        }
        commandText = parts.joined(separator: " ")
        sidecarPath = sidecarPathForJob
        queueVM.assignSidecar(jobID: next.id, sidecarPath: sidecarPathForJob)

        queueVM.markRunning(jobID: next.id)
        run()
    }

    private func makeSidecarPath(for audioURL: URL) -> String {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let sidecarDir = appDir.appendingPathComponent("sidecars", isDirectory: true)
        try? FileManager.default.createDirectory(at: sidecarDir, withIntermediateDirectories: true)
        let base = audioURL.deletingPathExtension().lastPathComponent
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let filename = "\(base)_\(timestamp).json"
        return sidecarDir.appendingPathComponent(filename).path
    }
}

public struct Metric: Identifiable, Hashable {
    public let id = UUID()
    public let label: String
    public let value: String
    public init(label: String, value: String) {
        self.label = label
        self.value = value
    }
}
