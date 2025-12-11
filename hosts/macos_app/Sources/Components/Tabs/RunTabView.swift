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
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
