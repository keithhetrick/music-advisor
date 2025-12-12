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

                if let warning = missingAudioWarning {
                    Text(warning)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.warning)
                        .padding(.horizontal, MAStyle.Spacing.sm)
                }

                workingDirectoryStatus

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
                }
                .padding(.trailing, MAStyle.Spacing.sm)
            }
        }
    }
}

private extension RunSplitView {
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
