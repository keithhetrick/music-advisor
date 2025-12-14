import SwiftUI
import AppKit
import MAStyle

struct RunTabView: View {
    @ObservedObject var store: AppStore
    @ObservedObject var viewModel: CommandViewModel
    let trackVM: TrackListViewModel?
    let pickFile: () -> URL?
    let pickDirectory: () -> URL?
    let revealSidecar: (String) -> Void
    let copyJSON: () -> Void
    let onPreviewRich: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            TrackHeaderView(title: store.state.mockTrackTitle, badgeText: "Norms Badge")
                .maSheen(isActive: viewModel.isRunning, duration: 5.5, highlight: Color.white.opacity(0.12))
            DropZoneView { urls in
                store.enqueueFromDrop(urls, baseCommand: viewModel.commandText)
            }
            JobQueueView(
                jobs: store.state.queueJobs,
                expandFoldersSignal: NotificationCenter.default.publisher(for: .uiTestExpandFolders),
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
                onRemove: { jobID in
                    store.removeJob(jobID)
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
            QuickActionsView(actions: store.state.quickActions)
            SectionsView(sections: store.state.sections)
            if let trackVM {
                TrackListView(viewModel: trackVM)
            }
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
            RunControlsView(
                isRunning: viewModel.isRunning,
                status: viewModel.status,
                lastRunTime: viewModel.lastRunTime,
                lastDuration: viewModel.lastDuration,
                onRun: {
                    Task { @MainActor in viewModel.run() }
                },
                onRunDefaults: {
                    Task { @MainActor in
                        viewModel.loadDefaults()
                        viewModel.run()
                    }
                },
                onRunSmoke: {
                    Task { @MainActor in viewModel.runSmoke() }
                }
            )
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
            echoStatusView
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var echoStatusView: some View {
        let statuses = Array(store.state.echoStatuses.values).sorted { $0.trackId < $1.trackId }
        return VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text("Historical Echo (broker)").maText(.headline)
                Spacer()
                Text("\(statuses.count) tracked")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
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
        .maCardInteractive()
    }

    private func echoStatusRow(_ status: EchoStatus) -> some View {
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
            if let err = status.error {
                Text("error: \(err)").maText(.caption).foregroundStyle(Color.red)
            }
        }
        .padding(MAStyle.Spacing.xs)
        .background(Color.gray.opacity(0.06))
        .cornerRadius(6)
    }

    private func color(for status: String) -> Color {
        switch status.lowercased() {
        case "done": return Color.green
        case "error", "timeout": return Color.red
        default: return Color.orange
        }
    }

    private func artifactURL(for artifact: String) -> URL? {
        let base = ProcessInfo.processInfo.environment["MA_ECHO_BROKER_URL"] ?? "http://127.0.0.1:8091"
        if artifact.hasPrefix("http") {
            return URL(string: artifact)
        }
        let trimmed = artifact.hasPrefix("/") ? String(artifact.dropFirst()) : artifact
        return URL(string: "\(base)/\(trimmed)")
    }
}
