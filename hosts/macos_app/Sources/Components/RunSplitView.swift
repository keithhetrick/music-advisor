import SwiftUI
import MAStyle
import UniformTypeIdentifiers

struct RunSplitView: View {
    @ObservedObject var store: AppStore
    @ObservedObject var viewModel: CommandViewModel
    let trackVM: TrackListViewModel?
    let pickFile: () -> URL?
    let pickDirectory: () -> URL?
    let revealSidecar: (String) -> Void
    let copyJSON: () -> Void
    let onPreviewRich: (String) -> Void

    var body: some View {
        AdaptiveSplitView {
            leftPane
        } right: {
            rightPane
        }
    }

    private var leftPane: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            TrackHeaderView(title: store.state.mockTrackTitle, badgeText: "Norms Badge")
                .maSheen(isActive: viewModel.isRunning, duration: 5.5, highlight: Color.white.opacity(0.12))
            DropZoneView { urls in
                viewModel.enqueue(files: urls)
            }
            JobQueueView(
                jobs: viewModel.queueVM.jobs,
                onReveal: revealSidecar,
                onPreviewRich: { richPath in onPreviewRich(richPath.replacingOccurrences(of: ".client.rich.txt", with: ".json")) },
                onClear: {
                    viewModel.queueVM.clear()
                    viewModel.currentJobID = nil
                }
            )
            QuickActionsView(actions: store.state.quickActions)
            SectionsView(sections: store.state.sections)
            if let trackVM {
                TrackListView(viewModel: trackVM)
            }
        }
    }

    private var rightPane: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
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
                },
                onToggleTheme: {
                    store.dispatch(.setTheme(!store.state.useDarkTheme))
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
    }
}
