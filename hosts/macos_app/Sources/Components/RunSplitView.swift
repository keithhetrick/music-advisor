import SwiftUI
import MAStyle

struct RunSplitView: View {
    @ObservedObject var store: AppStore
    @ObservedObject var viewModel: CommandViewModel
    let trackVM: TrackListViewModel?
    let pickFile: () -> URL?
    let pickDirectory: () -> URL?
    let revealSidecar: (String) -> Void
    let copyJSON: () -> Void
    let onPreviewRich: (String) -> Void
    let canRun: Bool
    let disabledReason: String?
    let runWarnings: [String]
    let missingAudioWarning: String?
    var onPickAudio: (() -> URL?)? = nil
    var onShowHistory: (() -> Void)? = nil
    @State private var showDetails: Bool = false
    @State private var isEnqueuingDrop: Bool = false
    @State private var showEchoPanel: Bool = true
    @State private var retryingFetch: Set<String> = []
    @State private var showResetIngestConfirm: Bool = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
                DropZoneView { urls in
                    isEnqueuingDrop = true
                    store.enqueueFromDrop(urls, baseCommand: viewModel.commandText)
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                        isEnqueuingDrop = false
                    }
                }
                .maCard(enableLens: false)
                .maHoverLift(enabled: false)
                .frame(maxWidth: .infinity)
                .frame(height: 80)

                if let warning = missingAudioWarning {
                    Text(warning)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.warning)
                        .padding(.horizontal, MAStyle.Spacing.sm)
                }

                workingDirectoryStatus
                    .padding(.horizontal, MAStyle.Spacing.sm)

                JobQueueView(
                    jobs: store.state.queueJobs,
                    isEnqueuing: isEnqueuingDrop,
                    ingestPendingCount: store.state.ingestPendingCount,
                    ingestErrorCount: store.state.ingestErrorCount,
                    onReveal: revealSidecar,
                    onPreviewRich: { richPath in onPreviewRich(richPath.replacingOccurrences(of: ".client.rich.txt", with: ".json")) },
                    onClear: {
                        store.clearQueueAll()
                    },
                    onStart: {
                        store.startQueue()
                    },
                    onStop: {
                        store.stopQueue()
                    },
                    onRemove: { id in
                        store.clearQueueAll() // removal per-job not yet exposed
                    },
                    onCancelPending: {
                        store.cancelPendingQueue()
                    },
                    onClearCompleted: {
                        store.clearQueueCompleted()
                    },
                    onClearCanceledFailed: {
                        store.clearQueueCanceledFailed()
                    },
                    onResumeCanceled: {
                        store.resumeCanceledQueue()
                    }
                )
                .maCard(enableLens: false)
                .maHoverLift(enabled: false)
                .frame(maxWidth: .infinity)

                CommandInputsView(
                    profiles: viewModel.profiles,
                    selectedProfile: Binding(get: { viewModel.selectedProfile },
                                             set: { viewModel.selectedProfile = $0 }),
                    onApplyProfile: {
                        Task { @MainActor in
                            viewModel.applySelectedProfile()
                        }
                    },
                    onReloadConfig: {
                        Task { @MainActor in
                            viewModel.reloadConfig()
                        }
                    },
                    showAdvanced: Binding(get: { store.state.showAdvanced },
                                          set: { store.dispatch(.setShowAdvanced($0)) }),
                    commandText: Binding(get: { viewModel.commandText },
                                         set: { viewModel.commandText = $0 }),
                    workingDirectory: Binding(get: { viewModel.workingDirectory },
                                              set: { viewModel.workingDirectory = $0 }),
                    envText: Binding(get: { viewModel.envText },
                                     set: { viewModel.envText = $0 }),
                    onPickAudio: {
                        if let url = pickFile() { viewModel.insertAudioPath(url.path) }
                    },
                    onBrowseDir: {
                        if let url = pickDirectory() { viewModel.setWorkingDirectory(url.path) }
                    }
                )
                .maCard(enableLens: false)
                .maHoverLift(enabled: false)
                .frame(maxWidth: .infinity)

                ResultsView(
                    selectedPane: Binding(get: { store.state.route.runPane },
                                          set: { pane in
                                              store.dispatch(.setRoute(store.state.route.updatingRunPane(pane)))
                                          }),
                    parsedJSON: viewModel.parsedJSON,
                    stdout: viewModel.stdout,
                    stderr: viewModel.stderr,
                    exitCode: viewModel.exitCode,
                    summaryMetrics: viewModel.summaryMetrics,
                    sidecarPath: viewModel.sidecarPath,
                    sidecarPreview: viewModel.sidecarPreview,
                    onRevealSidecar: {
                        if let path = viewModel.sidecarPath { revealSidecar(path) }
                    },
                    onCopySidecarPath: {
                        if let path = viewModel.sidecarPath {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(path, forType: .string)
                        }
                    },
                    onPreviewSidecar: {
                        Task { @MainActor in viewModel.loadSidecarPreview() }
                    },
                    onCopyJSON: copyJSON
                )
                .maCard()
                .maHoverLift(enabled: false)
                .frame(maxWidth: .infinity)

                if showEchoPanel {
                    echoStatusCard
                        .maCard()
                        .maHoverLift(enabled: false)
                } else {
                    HStack {
                        Text("Historical Echo (broker) hidden").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                        Spacer()
                        Button("Show Echo") { showEchoPanel = true }.maButton(.ghost)
                    }
                    .padding(.horizontal, MAStyle.Spacing.sm)
                }

                DisclosureGroup(isExpanded: $showDetails) {
                    VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                        RunConsoleView(stdout: viewModel.stdout, stderr: viewModel.stderr)
                        QuickActionsView(actions: store.state.quickActions)
                        SectionsView(sections: store.state.sections)
                    }
                } label: {
                    HStack {
                        Text("Console & details")
                            .maText(.body)
                        Spacer()
                        if showDetails {
                            Text("Tap to collapse")
                                .maText(.caption)
                                .foregroundStyle(MAStyle.ColorToken.muted)
                        }
                    }
                }
                .maCard()

                if let trackVM = trackVM {
                    TrackListView(viewModel: trackVM)
                        .maCard()
                }
            }
            .padding(.vertical, MAStyle.Spacing.sm)
        }
        .safeAreaInset(edge: .top) {
            RunControlsView(
                isRunning: viewModel.isRunning,
                status: viewModel.status,
                lastRunTime: viewModel.lastRunTime,
                lastDuration: viewModel.lastDuration,
                canRun: canRun,
                disabledReason: disabledReason,
                warnings: runWarnings,
                onRun: {
                    Task { @MainActor in viewModel.runQueueOrSingle() }
                },
                onRunDefaults: {
                    Task { @MainActor in
                        viewModel.loadDefaults()
                        viewModel.runQueueOrSingle()
                    }
                },
                onRunSmoke: {
                    Task { @MainActor in viewModel.runSmoke() }
                },
                onRevealLastSidecar: {
                    if let path = viewModel.sidecarPath { revealSidecar(path) }
                }
            )
            .padding(.horizontal, MAStyle.Spacing.md)
            .padding(.vertical, MAStyle.Spacing.sm)
            .background(
                MAStyle.ColorToken.panel.opacity(0.85)
                    .blur(radius: 0)
            )
            .overlay(alignment: .trailing) {
                HStack(spacing: MAStyle.Spacing.xs) {
                    if let onPickAudio = onPickAudio {
                        Button("Pick audio…") { _ = onPickAudio() }
                            .maButton(.secondary)
                    }
                    if let onShowHistory = onShowHistory {
                        Button("History", action: onShowHistory)
                            .maButton(.ghost)
                    }
                    Button("Reset ingest state") {
                        showResetIngestConfirm = true
                    }
                    .maButton(.ghost)
                }
                .padding(.trailing, MAStyle.Spacing.sm)
            }
        }
        .confirmationDialog(
            "Reset ingest state?",
            isPresented: $showResetIngestConfirm,
            titleVisibility: .visible
        ) {
            Button("Reset (destructive)", role: .destructive) {
                store.clearQueueAll()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will clear pending/failed queue entries and ingest state. Use only if you want a clean slate.")
        }
    }
}

private extension RunSplitView {
    var echoStatusCard: some View {
        let statuses = Array(store.state.echoStatuses.values).sorted { $0.trackId < $1.trackId }
        return VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text("Historical Echo (broker)").maText(.headline)
                Spacer()
                Text("\(statuses.count) tracked")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                Button(showEchoPanel ? "Hide" : "Show") {
                    showEchoPanel.toggle()
                }
                .maButton(.ghost)
            }
            let cachePath = cacheBasePath()
            Text("Cache base: \(cachePath)")
                .maText(.caption)
                .foregroundStyle(isSandboxPath(cachePath) ? MAStyle.ColorToken.warning : MAStyle.ColorToken.muted)
            if isSandboxPath(cachePath) {
                Text("Using sandboxed HOME; real HOME cache lives in ~/Library/Application Support/MusicAdvisorMacApp/echo_cache")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.warning)
            }
            if statuses.isEmpty {
                Text("No broker submissions yet.")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            } else {
                ForEach(statuses, id: \.trackId) { status in
                    echoStatusRow(status)
                }
            }
        }
    }

    func echoStatusRow(_ status: EchoStatus) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                Text(status.trackId).maText(.body)
                Spacer()
                Text(status.status.uppercased())
                    .maText(.caption)
                    .foregroundStyle(color(for: status.status))
            }
            if let job = status.jobId {
                Text("job_id: \(job)").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
            }
            if let cfg = status.configHash, let src = status.sourceHash {
                let cfgShort = String(cfg.prefix(8))
                let srcShort = String(src.prefix(8))
                Text("config: \(cfgShort)…  source: \(srcShort)…").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
            }
            if let n = status.neighborCount {
                Text("neighbors: \(n)").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
            }
            if let dec = status.decadeSummary {
                Text("decades: \(dec)").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
            }
            if let preview = status.neighborsPreview, !preview.isEmpty {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    Text("neighbors:").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                    ForEach(preview, id: \.self) { line in
                        Text("• \(line)").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                    }
                }
            }
            if let art = status.artifact {
                Text("artifact: \(art)").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
            }
            if let cached = status.cachedPath {
                HStack(spacing: MAStyle.Spacing.xs) {
                    Text("cached: \(cached)").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                    Button("Copy path") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(cached, forType: .string)
                    }
                    .maButton(.ghost)
                    Button("Open") {
                        NSWorkspace.shared.open(URL(fileURLWithPath: cached))
                    }
                    .maButton(.ghost)
                }
            } else if let art = status.artifact, let url = artifactURL(for: art) {
                Button("View JSON") {
                    NSWorkspace.shared.open(url)
                }
                .maButton(.ghost)
            }
            HStack(spacing: MAStyle.Spacing.xs) {
                let isFetching = retryingFetch.contains(status.trackId)
                Button("Retry fetch") {
                    startRetryFetch(trackId: status.trackId)
                }
                .disabled(isFetching)
                .maButton(.ghost)
                if canRetrySubmit(status.trackId) && status.status != "done" {
                    Button("Retry submit") {
                        Task { await store.retryEchoSubmit(trackId: status.trackId) }
                    }
                    .maButton(.ghost)
                }
                if isFetching {
                    ProgressView()
                        .scaleEffect(0.6)
                } else if status.status == "error" || status.status == "timeout" {
                    Text("retry if stale or failed").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                }
            }
            if let err = status.error {
                Text("error: \(err)").maText(.caption).foregroundStyle(Color.red)
            }
        }
        .padding(MAStyle.Spacing.xs)
        .background(Color.gray.opacity(0.06))
        .cornerRadius(6)
    }

    func color(for status: String) -> Color {
        switch status.lowercased() {
        case "done": return Color.green
        case "no_features": return Color.yellow
        case "error", "timeout": return Color.red
        default: return Color.orange
        }
    }

    func artifactURL(for artifact: String) -> URL? {
        let base = ProcessInfo.processInfo.environment["MA_ECHO_BROKER_URL"] ?? "http://127.0.0.1:8091"
        if artifact.hasPrefix("http") {
            return URL(string: artifact)
        }
        let trimmed = artifact.hasPrefix("/") ? String(artifact.dropFirst()) : artifact
        return URL(string: "\(base)/\(trimmed)")
    }

    func startRetryFetch(trackId: String) {
        if retryingFetch.contains(trackId) { return }
        retryingFetch.insert(trackId)
        Task {
            defer {
                Task { @MainActor in retryingFetch.remove(trackId) }
            }
            await store.retryEchoFetch(trackId: trackId)
        }
    }

    func canRetrySubmit(_ trackId: String) -> Bool {
        return store.state.queueJobs.contains { $0.displayName == trackId && $0.sidecarPath != nil }
    }

    func cacheBasePath() -> String {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?
            .appendingPathComponent("MusicAdvisorMacApp/echo_cache", isDirectory: true)
        return dir?.path ?? "(unknown)"
    }

    func isSandboxPath(_ path: String) -> Bool {
        return path.contains("/hosts/macos_app/build/home")
    }

    var workingDirectoryStatus: some View {
        let trimmed = viewModel.workingDirectory.trimmingCharacters(in: .whitespacesAndNewlines)
        let exists = !trimmed.isEmpty && FileManager.default.fileExists(atPath: trimmed)
        let label: String
        let color: Color
        if trimmed.isEmpty {
            label = "Working directory not set."
            color = MAStyle.ColorToken.warning
        } else if exists {
            label = "Working directory OK: \(trimmed)"
            color = MAStyle.ColorToken.muted
        } else {
            label = "Working directory missing: \(trimmed)"
            color = MAStyle.ColorToken.danger
        }
        return Text(label)
            .maText(.caption)
            .foregroundStyle(color)
            .padding(.horizontal, MAStyle.Spacing.sm)
    }
}
