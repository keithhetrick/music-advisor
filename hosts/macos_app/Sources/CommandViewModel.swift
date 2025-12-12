import Foundation
import SwiftUI
import MAStyle
import Combine
import MAQueue

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
    private var stopAfterCurrent: Bool = false
    private var progressThrottle = Date.distantPast
    var cancellables = Set<AnyCancellable>()
    private var currentTempSidecarPath: String?

    let runnerService: RunnerService
    private let initialConfig: AppConfig
    private let queuePersistence = QueuePersistence()
    private var logBuffer = PassthroughSubject<(String, Bool), Never>() // (line, isStdErr)
    private var logCancellable: AnyCancellable?
    private let logLimit = 10_000
    // Optional updater for processing snapshots (actor in AppStore).
    var processingUpdater: ((String?, Double?, String?) -> Void)?
    // Optional hook for when a job finishes; used to ingest into Tracks after success.
    var jobCompletionHandler: ((Job, Bool) -> Void)?

    init(config: AppConfig = .fromEnv()) {
        self.initialConfig = config
        self.runnerService = RunnerService(config: config)
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

        let persisted = queuePersistence.load()
        if !persisted.isEmpty {
            queueVM.replaceAll(persisted)
        }

        logCancellable = logBuffer
            .collect(.byTime(DispatchQueue.main, .milliseconds(300)))
            .sink { [weak self] batch in
                guard let self else { return }
                let stdoutLines = batch.filter { !$0.1 }.map { $0.0 }.joined(separator: "\n")
                let stderrLines = batch.filter { $0.1 }.map { $0.0 }.joined(separator: "\n")
                if !stdoutLines.isEmpty {
                    self.stdout.append(stdoutLines + "\n")
                    if self.stdout.count > self.logLimit {
                        self.stdout = String(self.stdout.suffix(self.logLimit))
                    }
                }
                if !stderrLines.isEmpty {
                    self.stderr.append(stderrLines + "\n")
                    if self.stderr.count > self.logLimit {
                        self.stderr = String(self.stderr.suffix(self.logLimit))
                    }
                }
            }

        queueVM.jobsPublisher
            .dropFirst()
            .sink { [weak self] jobs in
                self?.queuePersistence.save(jobs)
            }
            .store(in: &cancellables)
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
                // Surface to UI via optional processing updater.
                processingUpdater?("failed", 1.0, status)
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
            processingUpdater?("running", 0.0, "starting")

            let cwd = self.workingDirectory.isEmpty ? (self.initialConfig.workingDirectory ?? FileManager.default.currentDirectoryPath) : self.workingDirectory

            // Fail fast if the executable is missing/unusable; encourages proper runtime config.
            if let exe = parsedCommand.first, !FileManager.default.isExecutableFile(atPath: exe) {
                status = "Command not found or not executable: \(exe). Configure MA_APP_DEFAULT_CMD/WORKDIR or override via env."
                processingUpdater?("failed", 1.0, status)
                return
            }

            Task.detached { [cwd] in
                let start = Date()
                let result = await self.runnerService.run(command: parsedCommand,
                                                          workingDirectory: cwd,
                                                          extraEnv: env)
                let duration = Date().timeIntervalSince(start)
                // Parse heavy-ish work off the main actor.
                let parsed = await self.parseJSON(result.stdout)
                let metrics = await self.extractMetrics(from: parsed)

                await MainActor.run {
                    if let spawnError = result.spawnError {
                        self.stderr = spawnError
                        self.status = "Failed to start: \(spawnError)"
                        self.exitCode = result.exitCode
                        self.isRunning = false
                        self.processingUpdater?("failed", 1.0, self.status)
                    } else {
                        self.lastDuration = duration
                        self.stdout = result.stdout
                        self.stderr = result.stderr
                        self.exitCode = result.exitCode
                        self.status = "Done (exit \(result.exitCode))"
                    }
                self.parsedJSON = parsed
                self.summaryMetrics = metrics
                self.lastRunTime = Date()
                self.isRunning = false
                self.processingUpdater?(result.exitCode == 0 ? "done" : "failed", 1.0, self.status)
                if let spawnError = result.spawnError {
                    self.stderr = spawnError
                    self.status = "Failed to start: \(spawnError)"
                }

                if let jobID = self.currentJobID {
                    let job = self.queueVM.jobs.first(where: { $0.id == jobID })
                    let wasCanceled = job?.status == .canceled
                    let tempSidecarPath = self.currentTempSidecarPath
                    if result.exitCode == 0 && !wasCanceled {
                        self.finishSidecar(tempPath: tempSidecarPath, finalPath: self.sidecarPath)
                        self.queueVM.markDone(jobID: jobID, sidecarPath: self.sidecarPath)
                        let updatedJob = self.queueVM.jobs.first(where: { $0.id == jobID })
                        if let jobToReport = updatedJob ?? job { self.jobCompletionHandler?(jobToReport, true) }
                        QueueLogger.shared.log(.debug, "job done \(job?.displayName ?? "") exit=\(result.exitCode)")
                    } else if !wasCanceled {
                        self.cleanupTempSidecar()
                        let err = self.stderr.isEmpty ? self.status : self.stderr
                        self.queueVM.markFailed(jobID: jobID, error: err)
                        let updatedJob = self.queueVM.jobs.first(where: { $0.id == jobID })
                        if let jobToReport = updatedJob ?? job { self.jobCompletionHandler?(jobToReport, false) }
                        QueueLogger.shared.log(.error, "job failed \(job?.displayName ?? "") exit=\(result.exitCode) err=\(err)")
                    } else {
                        self.cleanupTempSidecar()
                        QueueLogger.shared.log(.debug, "job canceled \(job?.displayName ?? "")")
                    }
                    self.currentTempSidecarPath = nil
                    self.currentJobID = nil
                    self.updateProcessingProgress(message: wasCanceled ? "canceled \(job?.displayName ?? "")" : "finished \(job?.displayName ?? "")")
                } else {
                    // Standalone run; clear processing state.
                    self.processingUpdater?("done", 1.0, self.status)
                }
            }
        }
    }

    func runQueueOrSingle() {
        // If the engine is wired, the UI should call into the engine directly. Keep standalone run.
        if queueVM.jobs.contains(where: { $0.status == .pending }) || currentJobID != nil {
            updateProcessingProgress(message: "starting queue (engine handles)")
        } else {
            currentJobID = nil
            run()
        }
    }

    func appendStdout(_ line: String) {
        logBuffer.send((line, false))
        if stdout.count > logLimit {
            stdout = String(stdout.suffix(logLimit))
        }
    }

    func appendStderr(_ line: String) {
        logBuffer.send((line, true))
        if stderr.count > logLimit {
            stderr = String(stderr.suffix(logLimit))
        }
    }

    func flushLogs() {
        // Combine pipeline is already time-based; hook left for explicit flush if needed later.
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

    private func expandSources(urls: [URL]) -> [(url: URL, groupName: String?, groupID: UUID?, groupRootPath: String?)] {
        var results: [(URL, String?, UUID?, String?)] = []
        let fm = FileManager.default
        for url in urls {
            var isDir: ObjCBool = false
            if fm.fileExists(atPath: url.path, isDirectory: &isDir), isDir.boolValue {
                let groupID = UUID()
                let rootName = url.lastPathComponent
                let rootPath = url.path
                if let enumerator = fm.enumerator(at: url, includingPropertiesForKeys: [.isRegularFileKey], options: [.skipsHiddenFiles]) {
                    for case let fileURL as URL in enumerator {
                        if let vals = try? fileURL.resourceValues(forKeys: [.isRegularFileKey]),
                           vals.isRegularFile == true {
                            results.append((fileURL, rootName, groupID, rootPath))
                        }
                    }
                }
            } else {
                results.append((url, nil, nil, nil))
            }
        }
        return results
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
            let result = await runnerService.run(command: ["/bin/zsh", scriptPath],
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
        // Delegated to QueueEngine (AppStore wires it); keep stub for compatibility.
        QueueLogger.shared.log(.debug, "enqueue called (stub; engine should handle)")
    }

    func startQueue() {
        // Delegated to QueueEngine
    }

    func stopQueue() {
        // Delegated to QueueEngine
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

    private func ensureSidecarDirectoryExists(path: String) {
        let dir = URL(fileURLWithPath: path).deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    }

    private func makeTempSidecarPath(for finalPath: String) -> String {
        let suffix = ".tmp-\(UUID().uuidString)"
        return finalPath + suffix
    }

    private func finishSidecar(tempPath: String?, finalPath: String?) {
        let fm = FileManager.default
        guard let finalPath else { return }
        ensureSidecarDirectoryExists(path: finalPath)
        // If the tool already wrote to finalPath, accept and clean temp if present.
        if fm.fileExists(atPath: finalPath) {
            if let tempPath, fm.fileExists(atPath: tempPath) {
                try? fm.removeItem(atPath: tempPath)
            }
            return
        }
        guard let tempPath else { return }
        guard fm.fileExists(atPath: tempPath) else { return }
        // Move atomically; if final exists now, prefer existing.
        if fm.fileExists(atPath: finalPath) {
            try? fm.removeItem(atPath: tempPath)
            return
        }
        do {
            try fm.moveItem(atPath: tempPath, toPath: finalPath)
        } catch {
            // Swallow; absence or contention shouldn’t fail the job.
        }
    }

    private func cleanupTempSidecar() {
        if let temp = currentTempSidecarPath {
            try? FileManager.default.removeItem(atPath: temp)
        }
    }

    private func updateProcessingProgress(message: String? = nil) {
        let total = queueVM.jobs.count
        guard total > 0 else {
            processingUpdater?("idle", 0.0, message)
            return
        }
        let completed = queueVM.jobs.filter { $0.status == .done }.count
        let failed = queueVM.jobs.filter { $0.status == .failed }.count
        let running = queueVM.jobs.contains { $0.status == .running }
        let baseProgress = Double(completed + failed) / Double(total)
        let progress = running ? min(0.99, baseProgress + 0.05) : baseProgress
        let status: String
        if running { status = "running" }
        else if completed + failed == total { status = "done" }
        else { status = "pending" }
        processingUpdater?(status, progress, message)
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
