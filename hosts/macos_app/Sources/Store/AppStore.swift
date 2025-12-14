import Foundation
import SwiftUI
import AppKit
import MAQueue

private func queueLog(_ message: String) {
    let ts = ISO8601DateFormatter().string(from: Date())
    let line = "[echo-broker] \(ts) \(message)\n"
    print(line.trimmingCharacters(in: .whitespacesAndNewlines))
    let home = ProcessInfo.processInfo.environment["HOME"] ?? NSHomeDirectory()
    let base = URL(fileURLWithPath: home)
        .appendingPathComponent("Library", isDirectory: true)
        .appendingPathComponent("Logs", isDirectory: true)
        .appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
    do {
        try FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        let url = base.appendingPathComponent("echo_broker.log", isDirectory: false)
        if let data = line.data(using: .utf8) {
            if FileManager.default.fileExists(atPath: url.path) {
                let handle = try FileHandle(forWritingTo: url)
                try handle.seekToEnd()
                try handle.write(contentsOf: data)
                try handle.close()
            } else {
                try data.write(to: url)
            }
        }
    } catch {
        // best-effort logging
    }
}

enum AppTab: String, CaseIterable {
    case run = "Pipeline"
    case history = "History"
    case style = "MAStyle"
}

enum AppAction {
    case setAlert(AlertState?)
    case setRoute(AppRoute)
    case setTheme(Bool)
    case setFollowSystemTheme(Bool)
    case setPrompt(String)
    case appendMessage(String)
    case setMessages([String])
    case setShowAdvanced(Bool)
    case setHistoryItems([SidecarItem])
    case setHistoryPreview(path: String, preview: HistoryPreview)
    case setPreviewCache(path: String, preview: HistoryPreview)
    case clearHistory
    case setHostSnapshot(HostSnapshot)
    case setEchoStatuses([String: EchoStatus])
    // Chat UI state
    case setChatBadge(title: String, subtitle: String)
    case setChatContextLabel(String)
    case setChatContextTimestamp(Date?)
    case setChatContextPath(String?)
    // Chat context
    case setChatSelection(String?)
    case setChatOverride(String?)
}

struct EchoStatus: Identifiable {
    var id: String { trackId }
    let trackId: String
    var jobId: String?
    var status: String
    var configHash: String?
    var sourceHash: String?
    var artifact: String?
    var manifest: String?
    var etag: String?
    var cachedPath: String?
    var error: String?
    var neighborCount: Int?
    var decadeSummary: String?
    var neighborsPreview: [String]?
}

struct AppState {
    var alert: AlertState? = nil
    var route: AppRoute = .run(.json)
    var useDarkTheme: Bool = true
    var followSystemTheme: Bool = true
    var promptText: String = ""
    var messages: [String] = ["Welcome to Music Advisor!"]
    var showAdvanced: Bool = false
    var historyItems: [SidecarItem] = []
    var historyPreviews: [String: HistoryPreview] = [:]
    var previewCache: [String: (HistoryPreview, Date?)] = [:]
    var hostSnapshot: HostSnapshot = .idle
    // UI literals made dynamic for future tweaks.
    var mockTrackTitle: String = "Track Title — Artist"
    var quickActions: [(title: String, symbol: String)] = [
        ("Warnings", "exclamationmark.triangle.fill"),
        ("Quick Actions", "bolt.fill"),
        ("Norms", "chart.bar.doc.horizontal.fill")
    ]
    var sections: [String] = ["HCI", "Axes", "Historical Echo", "Optimization / Plan"]
    // Chat context selection
    var chatSelection: String? = "none"
    var chatOverridePath: String? = nil
    var chatContextLabel: String = "No context"
    var chatBadgeTitle: String = "No context"
    var chatBadgeSubtitle: String = "No file"
    var chatContextLastUpdated: Date? = nil
    var chatContextPath: String? = nil
    // Ingest/outbox status
    var ingestPendingCount: Int = 0
    var ingestErrorCount: Int = 0
    // Queue jobs (engine-driven)
    var queueJobs: [Job] = []
    // Echo broker statuses by track_id
    var echoStatuses: [String: EchoStatus] = [:]
}

@MainActor
final class AppStore: ObservableObject {
    @Published var state = AppState()

    // Adapters to keep existing bindings working while we refactor views to scoped state later.
    let commandVM: CommandViewModel
    let trackVM: TrackListViewModel?
    private let hostCoordinator: HostCoordinator
    private var hostMonitorTask: Task<Void, Never>?
    private let ingestOutbox = IngestOutbox()
    private let historyStore = HistoryStore()
    private var recordedHistoryJobs = Set<UUID>()
    private var recordedBrokerJobs = Set<UUID>()
    private var ingestProcessor: IngestProcessor?
    var queueEngine: QueueEngine?
    private let uiTestQueueController: UITestQueueController?
    private let echoBrokerClient: EchoBrokerClient?
    private var echoBrokerEtags: [String: String] = [:]
    private static let isUITestMode = UITestSupport.isEnabled

    @MainActor
    private func updateEchoStatus(trackId: String, build: (inout EchoStatus) -> Void) {
        var status = state.echoStatuses[trackId] ?? EchoStatus(trackId: trackId,
                                                               jobId: nil,
                                                               status: "pending",
                                                               artifact: nil,
                                                               manifest: nil,
                                                               etag: nil,
                                                               cachedPath: nil,
                                                               error: nil,
                                                               neighborCount: nil,
                                                               decadeSummary: nil,
                                                               neighborsPreview: nil)
        build(&status)
        // If we don't yet have a cachedPath but one exists on disk, fill it in so UI can show Open/Copy.
        if status.cachedPath == nil {
            let cacheDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?
                .appendingPathComponent("MusicAdvisorMacApp/echo_cache", isDirectory: true)
            let safeTrack = trackId.replacingOccurrences(of: "/", with: "_")
            let fname = "\(safeTrack)_historical_echo.json"
            if let dir = cacheDir {
                let candidate = dir.appendingPathComponent(fname)
                if FileManager.default.fileExists(atPath: candidate.path) {
                    status.cachedPath = candidate.path
                    // If we can, derive a quick summary from the cached file.
                    if status.neighborCount == nil || status.decadeSummary == nil || status.neighborsPreview == nil {
                        if let data = try? Data(contentsOf: candidate) {
                            let summary = parseEchoSummary(data: data)
                            status.neighborCount = summary.neighborCount
                            status.decadeSummary = summary.decadeSummary
                            status.neighborsPreview = summary.neighborsPreview
                        }
                    }
                }
            }
        }
        state.echoStatuses[trackId] = status
    }

    func dispatch(_ action: AppAction) {
        reduce(&state, action: action)
    }

    init(uiTestMode: Bool = AppStore.isUITestMode) {
        self.hostCoordinator = HostCoordinator()
        self.commandVM = CommandViewModel()
        let brokerEnabled = ProcessInfo.processInfo.environment["MA_ECHO_BROKER_ENABLE"] == "1"
        self.echoBrokerClient = brokerEnabled ? EchoBrokerClient(config: .fromEnv()) : nil
        if uiTestMode {
            self.trackVM = nil
            let controller = UITestSupport.makeQueueController()
            self.uiTestQueueController = controller
            self.queueEngine = nil
            controller.$jobs
                .receive(on: DispatchQueue.main)
                .sink { [weak self] jobs in
                    self?.state.queueJobs = jobs
                }
                .store(in: &commandVM.cancellables)
            state.queueJobs = controller.jobs
            state.alert = AlertHelper.toast("UI test toast", message: "Injected from UITest mode", level: .info)
            state.messages = ["UI Test Harness Loaded"]
            state.hostSnapshot = .idle
        } else {
            self.uiTestQueueController = nil
            self.trackVM = AppStore.makeTrackViewModel()
            if let trackVM {
                let sink = TrackVMIngestSink(trackVM: trackVM)
                let resolver = SidecarResolverAdapter()
                let runner = CommandRunnerAdapter(runner: self.commandVM.runnerService)
                self.queueEngine = QueueEngine(runner: runner,
                                               ingestor: sink,
                                               resolver: resolver,
                                               persistence: QueuePersistence(),
                                               outbox: ingestOutbox,
                                               metricsHook: nil)
                // Bind engine jobs/metrics to state for UI.
                self.queueEngine?.$jobs
                    .receive(on: DispatchQueue.main)
                    .sink { [weak self] jobs in
                        guard let self else { return }
                        self.state.queueJobs = jobs
                        // Append history for newly completed jobs with sidecars.
                        let newlyDone = jobs.filter { $0.status == .done && $0.sidecarPath != nil && !self.recordedHistoryJobs.contains($0.id) }
                        for job in newlyDone {
                            self.recordedHistoryJobs.insert(job.id)
                            Task { await self.appendHistory(sidecarPath: job.sidecarPath, fileURL: job.fileURL) }
                        }
                        // Submit to broker for newly done jobs (with sidecar) that haven't been submitted yet.
                        let newlyDoneBroker = jobs.filter { $0.status == .done && $0.sidecarPath != nil && !self.recordedBrokerJobs.contains($0.id) }
                        for job in newlyDoneBroker {
                            self.recordedBrokerJobs.insert(job.id)
                            queueLog("broker submit queued: \(job.displayName) sidecar=\(job.sidecarPath ?? "nil")")
                            Task { await self.submitEchoBrokerIfEnabled(job: job) }
                        }
                    }
                    .store(in: &commandVM.cancellables)
                self.queueEngine?.$ingestPendingCount
                    .receive(on: DispatchQueue.main)
                    .sink { [weak self] count in
                        self?.state.ingestPendingCount = count
                    }
                    .store(in: &commandVM.cancellables)
                self.queueEngine?.$ingestErrorCount
                    .receive(on: DispatchQueue.main)
                    .sink { [weak self] count in
                        self?.state.ingestErrorCount = count
                    }
                    .store(in: &commandVM.cancellables)
            }
        }
        // Load persisted history on launch.
        state.historyItems = historyStore.load()
        // Seed theme from system appearance if following system.
        let systemDark = AppStore.systemPrefersDark()
        state.useDarkTheme = systemDark
        state.followSystemTheme = true
        self.commandVM.processingUpdater = { [weak self] status, progress, message in
            Task {
                await self?.hostCoordinator.updateProcessing(status: status, progress: progress, message: message)
            }
        }
        if !uiTestMode, let trackVM {
            self.commandVM.jobCompletionHandler = { job, success in
                let sidecarPath = job.sidecarPath ?? "nil"
                let sidecarExists = job.sidecarPath.flatMap { FileManager.default.fileExists(atPath: $0) } ?? false
                if let prepared = job.preparedCommand {
                    queueLog("jobCompletionHandler: \(job.displayName) success=\(success) status=\(job.status) sidecar=\(sidecarPath) exists=\(sidecarExists) prepared=\(prepared.joined(separator: " "))")
                } else {
                    queueLog("jobCompletionHandler: \(job.displayName) success=\(success) status=\(job.status) sidecar=\(sidecarPath) exists=\(sidecarExists)")
                }
                guard success, job.status == .done else { return }
                Task {
                    await self.ingestOutbox.enqueue(fileURL: job.fileURL, jobID: job.id)
                    await self.refreshOutboxCounts()
                    self.ingestProcessor?.kick()
                    await self.appendHistory(sidecarPath: job.sidecarPath, fileURL: job.fileURL)
                    await self.submitEchoBrokerIfEnabled(job: job)
                }
            }
            // Ensure track data is loaded even before the view appears (e.g., before scrolling).
            trackVM.load()
        }
        if !uiTestMode {
            startHostMonitor()
        }
        let homeEnv = ProcessInfo.processInfo.environment["HOME"] ?? "(nil)"
        let cwd = FileManager.default.currentDirectoryPath
        if brokerEnabled, echoBrokerClient != nil {
            let url = EchoBrokerClient.Config.fromEnv().baseURL
            queueLog("enabled url=\(url) home=\(homeEnv) cwd=\(cwd)")
            state.messages.append("Echo broker enabled")
        } else {
            queueLog("disabled (env not set or client nil) home=\(homeEnv) cwd=\(cwd)")
        }
    }

    deinit {
        hostMonitorTask?.cancel()
    }

    // MARK: - Queue helpers (shared by production + UI tests)

    func enqueueJobs(_ jobs: [Job]) {
        queueEngine?.enqueue(jobs)
        uiTestQueueController?.enqueue(jobs)
        if let queueEngine {
            state.queueJobs = queueEngine.jobs
        }
    }

    func enqueueFromDrop(_ urls: [URL], baseCommand: String) {
        let entries = expandSources(urls: urls)
        let jobs = JobsBuilder.makeJobs(from: entries, baseCommand: baseCommand)
        guard !jobs.isEmpty else { return }
        enqueueJobs(jobs)
    }

    @MainActor
    func retryEchoSubmit(trackId: String) async {
        guard let job = state.queueJobs.first(where: { $0.displayName == trackId && $0.sidecarPath != nil }) else {
            return
        }
        await submitEchoBrokerIfEnabled(job: job)
    }

    func startQueue() {
        queueEngine?.start()
        uiTestQueueController?.start()
    }

    func stopQueue() {
        queueEngine?.stop()
        uiTestQueueController?.stop()
    }

    func cancelPendingQueue() {
        queueEngine?.stop()
        uiTestQueueController?.cancelPending()
    }

    private func resolveRepoRoot() -> URL {
        let env = ProcessInfo.processInfo.environment
        if let repo = env["REPO"], !repo.isEmpty {
            return URL(fileURLWithPath: repo)
        }
        if let pwd = env["PWD"], !pwd.isEmpty {
            return URL(fileURLWithPath: pwd)
        }
        let cwd = FileManager.default.currentDirectoryPath
        if !cwd.isEmpty {
            return URL(fileURLWithPath: cwd)
        }
        return FileManager.default.homeDirectoryForCurrentUser
    }

    func resumeCanceledQueue() {
        queueEngine?.resumeCanceled()
        uiTestQueueController?.resumeCanceled()
    }

    /// Submit features to the local echo broker (opt-in via MA_ECHO_BROKER_ENABLE=1).
    private func submitEchoBrokerIfEnabled(job: Job) async {
        guard let client = echoBrokerClient else {
            print("[echo-broker] skipped: disabled")
            await MainActor.run { state.messages.append("Echo broker skipped: disabled") }
            return
        }
        var featuresPath: String?
        if let sidecarPath = job.sidecarPath, FileManager.default.fileExists(atPath: sidecarPath) {
            featuresPath = sidecarPath
        } else {
            // Fallback: if automator.sh was used, locate features.json under data/features_output/YYYY/MM/DD/<stem>
            if let cmd = job.preparedCommand, cmd.first?.hasSuffix("automator.sh") == true {
                let stem = job.fileURL.deletingPathExtension().lastPathComponent
                let now = Date()
                let cal = Calendar.current
                let comps = cal.dateComponents([.year, .month, .day], from: now)
                if let y = comps.year, let m = comps.month, let d = comps.day {
                    let repoRoot = resolveRepoRoot()
                    let outDir = repoRoot
                        .appendingPathComponent("data/features_output", isDirectory: true)
                        .appendingPathComponent(String(format: "%04d", y), isDirectory: true)
                        .appendingPathComponent(String(format: "%02d", m), isDirectory: true)
                        .appendingPathComponent(String(format: "%02d", d), isDirectory: true)
                        .appendingPathComponent(stem, isDirectory: true)
                    if let latest = latestFeaturesJSON(in: outDir) {
                        featuresPath = latest.path
                        queueLog("broker fallback features found: \(featuresPath!)")
                    } else {
                        queueLog("broker fallback features missing in \(outDir.path)")
                    }
                }
            }
        }
        guard let featPath = featuresPath, FileManager.default.fileExists(atPath: featPath) else {
            queueLog("Echo broker skipped: no features for \(job.displayName)")
            await MainActor.run {
                state.messages.append("Echo broker skipped: no features for \(job.displayName)")
                updateEchoStatus(trackId: job.displayName) { s in
                    s.status = "no_features"
                    s.error = "features not found"
                }
            }
            return
        }
        let trackId = job.displayName
        do {
            let resp = try await client.submitJob(featuresPath: URL(fileURLWithPath: featPath), trackId: trackId, probe: [:], dbPath: nil, configHash: nil, runId: nil)
            print("[echo-broker] submitted track_id=\(trackId) job_id=\(resp.jobId) path=\(featPath)")
            await MainActor.run {
                state.messages.append("Echo broker submitted for \(trackId) job_id=\(resp.jobId)")
                updateEchoStatus(trackId: trackId) { status in
                    status.jobId = resp.jobId
                    status.status = "pending"
                    status.error = nil
                }
            }
            Task.detached { [weak self] in
                await self?.pollEchoJobAndFetch(client: client, jobId: resp.jobId, trackId: trackId)
            }
        } catch {
            await MainActor.run {
                state.messages.append("Echo broker submit failed: \(error)")
                updateEchoStatus(trackId: trackId) { status in
                    status.status = "error"
                    status.error = "\(error)"
                }
            }
        }
    }

    /// Poll broker for completion and cache artifact with ETag.
    private func pollEchoJobAndFetch(client: EchoBrokerClient, jobId: String, trackId: String) async {
        var delay: UInt64 = 1_000_000_000  // 1s
        for _ in 0..<12 {  // ~1 minute max
            do {
                let status = try await client.fetchJob(jobId: jobId)
                if status.status == "done", let result = status.result, let artPath = result.artifactPath {
                    print("[echo-broker] done job_id=\(jobId) artifact=\(artPath)")
                    await MainActor.run {
                        state.messages.append("Echo broker done for \(trackId)")
                        updateEchoStatus(trackId: trackId) { s in
                            s.status = "done"
                            s.jobId = jobId
                            s.artifact = artPath
                            s.manifest = result.manifestPath
                        }
                    }
                    if let cachedPath = await fetchEchoArtifact(client: client, artifactPath: artPath, trackId: trackId) {
                        await MainActor.run {
                            state.messages.append("Echo artifact cached: \(cachedPath)")
                            updateEchoStatus(trackId: trackId) { s in
                                s.cachedPath = cachedPath
                            }
                        }
                    }
                    return
                }
                if status.status == "error" {
                    print("[echo-broker] error job_id=\(jobId) err=\(status.error ?? "unknown")")
                    await MainActor.run {
                        state.messages.append("Echo broker error for \(trackId): \(status.error ?? "unknown")")
                        updateEchoStatus(trackId: trackId) { s in
                            s.status = "error"
                            s.error = status.error ?? "unknown"
                        }
                    }
                    return
                }
            } catch {
                await MainActor.run {
                    state.messages.append("Echo broker poll failed: \(error)")
                    updateEchoStatus(trackId: trackId) { s in
                        s.status = "error"
                        s.error = "\(error)"
                    }
                }
            }
            try? await Task.sleep(nanoseconds: delay)
            delay = min(delay * 2, 8_000_000_000)  // cap at 8s
        }
        await MainActor.run {
            state.messages.append("Echo broker timed out for \(trackId)")
            updateEchoStatus(trackId: trackId) { s in
                s.status = "timeout"
            }
        }
    }

    /// Fetch artifact via broker with ETag and cache to disk.
    private func fetchEchoArtifact(client: EchoBrokerClient, artifactPath: String, trackId: String) async -> String? {
        // artifactPath looks like .../echo/<config_hash>/<source_hash>/historical_echo.json
        let comps = artifactPath.split(separator: "/")
        guard comps.count >= 3 else {
            await MainActor.run {
                state.messages.append("Echo broker artifact path malformed for \(trackId)")
            }
            return nil
        }
        let sourceHash = String(comps[comps.count - 2])
        let configHash = String(comps[comps.count - 3])
        await MainActor.run {
            updateEchoStatus(trackId: trackId) { s in
                s.configHash = configHash
                s.sourceHash = sourceHash
            }
        }
        do {
            let etag = echoBrokerEtags[trackId]
            let result = try await client.fetchArtifact(configHash: configHash, sourceHash: sourceHash, etag: etag)
            echoBrokerEtags[trackId] = result.etag ?? etag
            let cached = cacheEchoArtifact(trackId: trackId, data: result.data)
            await MainActor.run {
                updateEchoStatus(trackId: trackId) { s in
                    s.etag = result.etag ?? etag
                    let summary = parseEchoSummary(data: result.data)
                    s.neighborCount = summary.neighborCount
                    s.decadeSummary = summary.decadeSummary
                    s.neighborsPreview = summary.neighborsPreview
                }
            }
            return cached
        } catch EchoBrokerClient.BrokerError.notModified {
            await MainActor.run {
                state.messages.append("Echo artifact up-to-date for \(trackId)")
                updateEchoStatus(trackId: trackId) { s in
                    s.status = "done"
                }
            }
            return nil
        } catch {
            await MainActor.run {
                state.messages.append("Echo broker fetch failed: \(error)")
                updateEchoStatus(trackId: trackId) { s in
                    s.status = "error"
                    s.error = "\(error)"
                }
            }
            return nil
        }
    }

    private func cacheEchoArtifact(trackId: String, data: Data) -> String {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let cacheDir = supportDir.appendingPathComponent("MusicAdvisorMacApp/echo_cache", isDirectory: true)
        try? FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
        let safeTrack = trackId.replacingOccurrences(of: "/", with: "_")
        let fname = "\(safeTrack)_historical_echo.json"
        let path = cacheDir.appendingPathComponent(fname)
        try? data.write(to: path)
        return path.path
    }

    func parseEchoSummary(data: Data) -> (neighborCount: Int?, decadeSummary: String?, neighborsPreview: [String]?) {
        guard
            let json = try? JSONSerialization.jsonObject(with: data, options: []),
            let dict = json as? [String: Any]
        else { return (nil, nil, nil) }
        let neighbors = dict["neighbors"] as? [Any] ?? []
        let neighborCount = neighbors.count
        var decadeSummary: String?
        var neighborsPreview: [String]?
        if let decades = dict["decade_counts"] as? [String: Any] {
            let parts = decades.compactMap { (k, v) -> String? in
                if let n = v as? Int { return "\(k): \(n)" }
                return nil
            }
            if !parts.isEmpty {
                decadeSummary = parts.sorted().joined(separator: ", ")
            }
        }
        if !neighbors.isEmpty {
            neighborsPreview = neighbors.prefix(5).compactMap { item -> String? in
                guard let n = item as? [String: Any] else { return nil }
                let artist = n["artist"] as? String ?? "?"
                let title = n["title"] as? String ?? "?"
                let dist = n["distance"] as? Double
                if let d = dist {
                    return "\(artist) – \(title) (d=\(String(format: "%.2f", d)))"
                }
                return "\(artist) – \(title)"
            }
        }
        return (neighborCount, decadeSummary, neighborsPreview)
    }

    // Manual refetch for a given track_id (uses artifact if present; otherwise fetchLatest then fetch artifact).
    @MainActor
    func retryEchoFetch(trackId: String) async {
        guard let client = echoBrokerClient else { return }
        var artifactPath = state.echoStatuses[trackId]?.artifact
        if artifactPath == nil {
            do {
                let latest = try await client.fetchLatest(trackId: trackId)
                artifactPath = latest.artifact
                updateEchoStatus(trackId: trackId) { s in
                    s.artifact = latest.artifact
                    s.manifest = latest.manifest
                    s.configHash = latest.configHash
                    s.sourceHash = latest.sourceHash
                    s.etag = latest.etag
                }
            } catch {
                updateEchoStatus(trackId: trackId) { s in
                    s.status = "error"
                    s.error = "\(error)"
                }
                return
            }
        }
        guard let art = artifactPath else { return }
        _ = await fetchEchoArtifact(client: client, artifactPath: art, trackId: trackId)
    }

    private func latestFeaturesJSON(in dir: URL) -> URL? {
        guard let contents = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.contentModificationDateKey], options: [.skipsHiddenFiles]) else {
            return nil
        }
        let candidates = contents.filter { $0.lastPathComponent.hasSuffix(".features.json") }
        return candidates.sorted {
            let a = (try? $0.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            let b = (try? $1.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            return a > b
        }.first
    }

    func clearQueueAll() {
        queueEngine?.resetAll()
        uiTestQueueController?.clearAll()
        state.queueJobs = []
        state.ingestPendingCount = 0
        state.ingestErrorCount = 0
        // Also wipe persisted queue/cache so badges reset on next launch.
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let queuePath = appDir.appendingPathComponent("queue.json")
        let previewCachePath = appDir.appendingPathComponent("preview_cache.json")
        let outboxPath = appDir.appendingPathComponent("ingest_outbox.json")
        try? FileManager.default.removeItem(at: queuePath)
        try? FileManager.default.removeItem(at: previewCachePath)
        try? FileManager.default.removeItem(at: outboxPath)
        Task {
            await ingestOutbox.reset()
            await MainActor.run {
                self.state.ingestPendingCount = 0
                self.state.ingestErrorCount = 0
                self.state.queueJobs = []
            }
        }
    }

    func clearQueueCompleted() {
        queueEngine?.clearCompleted()
        uiTestQueueController?.clearCompleted()
    }

    func clearQueueCanceledFailed() {
        queueEngine?.clearCanceledFailed()
        uiTestQueueController?.clearCanceledFailed()
    }

    private func appendHistory(sidecarPath: String?, fileURL: URL) async {
        guard let path = sidecarPath else { return }
        let fm = FileManager.default
        guard fm.fileExists(atPath: path) else { return }
        let attrs = try? fm.attributesOfItem(atPath: path)
        let modified = attrs?[.modificationDate] as? Date ?? Date()
        let item = SidecarItem(path: path, name: URL(fileURLWithPath: path).lastPathComponent, modified: modified)
        await MainActor.run {
            if !state.historyItems.contains(where: { $0.path == path }) {
                state.historyItems.insert(item, at: 0)
                historyStore.save(state.historyItems)
            }
        }
    }

    // Expand dropped URLs into file entries, grouping only when an actual folder was dropped.
    private func expandSources(urls: [URL]) -> [DropEntry] {
        var results: [DropEntry] = []
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
                            results.append(DropEntry(url: fileURL,
                                                     groupID: groupID,
                                                     groupName: rootName,
                                                     groupRoot: rootPath))
                        }
                    }
                }
            } else {
                results.append(DropEntry(url: url, groupID: nil, groupName: nil, groupRoot: nil))
            }
        }
        return results
    }

    func removeJob(_ id: UUID) {
        uiTestQueueController?.remove(id)
        if let controller = uiTestQueueController {
            state.queueJobs = controller.jobs
        }
    }

    func forceCanceledForUITests() {
        uiTestQueueController?.markPendingAsCanceled()
        if let controller = uiTestQueueController {
            state.queueJobs = controller.jobs
        }
    }

    func ensureResumeAvailableForUITests() {
        uiTestQueueController?.ensureResumeAvailable()
        if let controller = uiTestQueueController {
            state.queueJobs = controller.jobs
        }
    }

    func forceResumeCanceledForUITests() {
        uiTestQueueController?.forceResumeAndStart()
        if let controller = uiTestQueueController {
            state.queueJobs = controller.jobs
        }
    }

    func seedQueueForUITests() {
        uiTestQueueController?.seed()
        if let controller = uiTestQueueController {
            state.queueJobs = controller.jobs
        }
    }

    func enqueueSampleJobForUITests() {
        guard let controller = uiTestQueueController else { return }
        let job = UITestSupport.sampleJob(name: "ui-test.wav")
        try? FileManager.default.createDirectory(at: job.fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        FileManager.default.createFile(atPath: job.fileURL.path, contents: Data())
        controller.enqueue([job])
        state.queueJobs = controller.jobs
    }

    var isUITestHarnessActive: Bool {
        uiTestQueueController != nil
    }

    private static func trackStorePaths() -> (dbURL: URL, legacyTrackURL: URL, legacyArtistURL: URL) {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let dbURL = appDir.appendingPathComponent("MusicAdvisor.sqlite")
        let trackURL = appDir.appendingPathComponent("tracks.json")
        let artistURL = appDir.appendingPathComponent("artists.json")
        return (dbURL, trackURL, artistURL)
    }

    private static func makeTrackViewModel() -> TrackListViewModel {
        let paths = trackStorePaths()
        try? FileManager.default.createDirectory(at: paths.dbURL.deletingLastPathComponent(),
                                                 withIntermediateDirectories: true)
        let sqliteStore = try? SQLiteTrackStore(url: paths.dbURL)

        if let sqliteStore {
            migrateLegacyJSONIfNeeded(into: sqliteStore,
                                      trackURL: paths.legacyTrackURL,
                                      artistURL: paths.legacyArtistURL)
            return TrackListViewModel(trackStore: sqliteStore, artistStore: sqliteStore)
        } else {
            // Fall back to legacy JSON stores if SQLite init fails.
            let trackStore = JsonTrackStore(url: paths.legacyTrackURL)
            let artistStore = JsonArtistStore(url: paths.legacyArtistURL)
            return TrackListViewModel(trackStore: trackStore, artistStore: artistStore)
        }
    }

    private static func migrateLegacyJSONIfNeeded(into store: SQLiteTrackStore,
                                                  trackURL: URL,
                                                  artistURL: URL) {
        let jsonTrackStore = JsonTrackStore(url: trackURL)
        let jsonArtistStore = JsonArtistStore(url: artistURL)
        let hasExistingData = (try? store.listTracks().isEmpty == false) ?? false
        guard !hasExistingData else { return }
        guard FileManager.default.fileExists(atPath: trackURL.path) || FileManager.default.fileExists(atPath: artistURL.path) else {
            return
        }
        let artists = (try? jsonArtistStore.listArtists()) ?? []
        let tracks = (try? jsonTrackStore.listTracks()) ?? []
        for artist in artists {
            try? store.upsert(artist)
        }
        for track in tracks {
            try? store.upsert(track)
        }
    }

    private func startHostMonitor() {
        hostMonitorTask?.cancel()
        hostMonitorTask = Task.detached { [weak self] in
            while let self = self {
                let snap = await self.hostCoordinator.snapshot()
                await MainActor.run {
                    self.state.hostSnapshot = snap
                }
                // Back off polling when idle to reduce wakeups.
                let interval: UInt64 = snap.processing.status == "running" ? 1_500_000_000 : 3_500_000_000
                try? await Task.sleep(nanoseconds: interval)
            }
        }
    }

    func refreshOutboxCounts() async {
        let snapshot = await ingestOutbox.snapshot()
        await MainActor.run {
            state.ingestPendingCount = snapshot.pending
            state.ingestErrorCount = snapshot.errors
        }
    }
}

// MARK: - Reducer

private func reduce(_ state: inout AppState, action: AppAction) {
    switch action {
    case .setAlert(let alert):
        state.alert = alert
    case .setRoute(let route):
        state.route = route
    case .setTheme(let value):
        state.useDarkTheme = value
    case .setFollowSystemTheme(let value):
        state.followSystemTheme = value
    case .setPrompt(let text):
        state.promptText = text
    case .appendMessage(let msg):
        state.messages.append(msg)
        if state.messages.count > 200 {
            state.messages.removeFirst(state.messages.count - 200)
        }
    case .setMessages(let msgs):
        state.messages = msgs
    case .setShowAdvanced(let value):
        state.showAdvanced = value
    case .setHistoryItems(let items):
        state.historyItems = items
    case .setHistoryPreview(let path, let preview):
        state.historyPreviews[path] = preview
    case .setPreviewCache(let path, let preview):
        // Keep old mtime if present (will be overridden by caller when needed).
        let currentMtime = state.previewCache[path]?.1
        state.previewCache[path] = (preview, currentMtime)
    case .clearHistory:
        state.historyItems = []
        state.historyPreviews = [:]
        state.previewCache = [:]
    case .setHostSnapshot(let snap):
        state.hostSnapshot = snap
    case .setChatBadge(let title, let subtitle):
        state.chatBadgeTitle = title
        state.chatBadgeSubtitle = subtitle
    case .setChatContextLabel(let label):
        state.chatContextLabel = label
    case .setChatContextTimestamp(let ts):
        state.chatContextLastUpdated = ts
    case .setChatContextPath(let path):
        state.chatContextPath = path
    case .setChatSelection(let sel):
        state.chatSelection = sel
    case .setChatOverride(let path):
        state.chatOverridePath = path
    case .setEchoStatuses(let echo):
        state.echoStatuses = echo
    }
}

extension AppStore {
    static func systemPrefersDark() -> Bool {
        let best = NSApplication.shared.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua])
        return best == .darkAqua
    }
}
