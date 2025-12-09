import SwiftUI
import AppKit
import MAStyle

struct RunPanelView: View {
    @ObservedObject var store: AppStore
    @ObservedObject var viewModel: CommandViewModel
    let trackVM: TrackListViewModel?
    let mockTrackTitle: String
    let quickActions: [(title: String, symbol: String)]
    let sections: [String]
    var pickFile: () -> URL?
    var pickDirectory: () -> URL?
    var revealSidecar: (String) -> Void
    var copyJSON: () -> Void
    var onPreviewRich: (String) -> Void

    var body: some View {
        HStack(alignment: .top, spacing: MAStyle.Spacing.md) {
            leftColumn
                .frame(maxWidth: 260)
                .maCardInteractive()
            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                CardHeader(title: mockTrackTitle, badge: "Norms")
                    .maSheen(isActive: viewModel.isRunning, duration: 5.5, highlight: Color.white.opacity(0.12))
                DropZoneView { urls in
                    viewModel.enqueue(files: urls)
                    trackVM?.ingestDropped(urls: urls)
                }
                .maCardInteractive()

                HStack(spacing: MAStyle.Spacing.sm) {
                    Button("Add file to queue") {
                        if let url = pickFile() {
                            viewModel.enqueue(files: [url])
                            trackVM?.ingestDropped(urls: [url])
                        }
                    }
                    .maButton(.ghost)
                    Button("Add folder…") {
                        if let dir = pickDirectory() {
                            let urls = (try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? []
                            viewModel.enqueue(files: urls)
                            trackVM?.ingestDropped(urls: urls)
                        }
                    }
                    .maButton(.ghost)
                    Button("Start batch") {
                        viewModel.startQueue()
                    }
                    .maButton(.primary)
                    .disabled(viewModel.isRunning || viewModel.queueVM.jobs.allSatisfy { $0.status != .pending })
                    Button("Stop after current") {
                        viewModel.stopQueue()
                    }
                    .maButton(.ghost)
                }

                CollapsibleCard {
                    CardHeader(title: "Batch Queue")
                } content: {
                    JobQueueView(
                        jobs: viewModel.queueVM.jobs,
                        onReveal: revealSidecar,
                        onPreviewRich: { richPath in
                            let sidecar = richPath.replacingOccurrences(of: ".client.rich.txt", with: ".json")
                            onPreviewRich(sidecar)
                        },
                        onClear: {
                            viewModel.queueVM.clear()
                            viewModel.currentJobID = nil
                        }
                    )
                }
                .maCardInteractive()

                CollapsibleCard {
                    CardHeader(title: "Quick Actions")
                } content: {
                    QuickActionsView(actions: quickActions)
                }
                .maCardInteractive()
                CollapsibleCard {
                    CardHeader(title: "Sections")
                } content: {
                    SectionsView(sections: sections)
                }
                .maCardInteractive()

                if let trackVM {
                CollapsibleCard {
                    CardHeader(title: "Tracks")
                } content: {
                    TrackListView(viewModel: trackVM)
                }
                .maCardInteractive()
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
                        if let url = pickFile() {
                            viewModel.insertAudioPath(url.path)
                        }
                    },
                    onBrowseDir: {
                        if let url = pickDirectory() {
                            viewModel.setWorkingDirectory(url.path)
                        }
                    }
                )
                .maCardInteractive()

                VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
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
                    .maCard()

                    HStack(spacing: MAStyle.Spacing.sm) {
                        Button("Run picked file…") {
                            if let url = pickFile() {
                                viewModel.insertAudioPath(url.path)
                                Task { @MainActor in viewModel.run() }
                            }
                        }
                        .maButton(.primary)
                        .disabled(viewModel.isRunning)
                        Text("Runs immediately with selected profile and last settings.")
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                        Button("Run pipeline") {
                            Task { @MainActor in
                                viewModel.run()
                            }
                        }
                        .maButton(.secondary)
                        .disabled(viewModel.isRunning)
                    }
                    .maCardInteractive()

                    resultsSectionView
                        .maCardInteractive()
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var leftColumn: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            ConsoleView(messages: store.state.messages)
            PromptBar(
                text: Binding(get: { store.state.promptText },
                              set: { store.dispatch(.setPrompt($0)) }),
                placeholder: "Type a command or note…",
                isThinking: viewModel.isRunning,
                focus: nil,
                onSend: sendMessage,
                onClear: { store.dispatch(.setPrompt("")) }
            )
        }
    }

    private func sendMessage() {
        let trimmed = store.state.promptText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        store.dispatch(.appendMessage(trimmed))
        store.dispatch(.setPrompt(""))
    }

    private func loadHistoryPreview(path: String) {
        onPreviewRich(path)
    }

    private var resultsSectionView: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Result").maText(.headline)
            Picker("", selection: Binding(get: { store.state.route.runPane },
                                          set: { pane in
                                              store.dispatch(.setRoute(store.state.route.updatingRunPane(pane)))
                                          })) {
                Text("JSON").tag(ResultPane.json)
                Text("stdout").tag(ResultPane.stdout)
                Text("stderr").tag(ResultPane.stderr)
            }
            .pickerStyle(.segmented)

            if !viewModel.summaryMetrics.isEmpty || viewModel.sidecarPath != nil {
                HStack(spacing: MAStyle.Spacing.sm) {
                    ForEach(viewModel.summaryMetrics) { metric in
                        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                            Text(metric.label).maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                            Text(metric.value).maText(.body)
                        }
                        .maMetric()
                    }
                    if let path = viewModel.sidecarPath {
                        Button("Reveal sidecar") { revealSidecar(path) }.maButton(.ghost)
                        Button("Copy path") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(path, forType: .string)
                        }
                        .maButton(.ghost)
                        Button("Preview sidecar") {
                            _ = Task { @MainActor in viewModel.loadSidecarPreview() }
                        }
                        .maButton(.ghost)
                    }
                    Spacer()
                }
            }

            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Copy JSON") { copyJSON() }
                    .maButton(.ghost)
                    .disabled(viewModel.parsedJSON.isEmpty)
                if let path = viewModel.sidecarPath {
                    Button("Copy sidecar path") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(path, forType: .string)
                    }
                    .maButton(.ghost)
                }
                Spacer()
            }

            resultBlock(title: store.state.route.runPane.title,
                        text: paneText(store.state.route.runPane),
                        color: store.state.route.runPane.color)

            if !viewModel.sidecarPreview.isEmpty {
                resultBlock(title: "sidecar preview",
                            text: viewModel.sidecarPreview,
                            color: .purple)
            }

            Text("Exit code: \(viewModel.exitCode)")
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
    }

    private func resultBlock(title: String, text: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title).font(MAStyle.Typography.headline)
            ScrollView {
                Text(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "(empty)" : text.trimmingCharacters(in: .whitespacesAndNewlines))
                    .font(MAStyle.Typography.bodyMono)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(MAStyle.Spacing.sm)
                    .maCardInteractive()
            }
            .frame(minHeight: 80)
        }
    }

    private func paneText(_ pane: ResultPane) -> String {
        switch pane {
        case .json:
            return viewModel.parsedJSON.isEmpty ? "(no JSON parsed)" : prettyJSON(viewModel.parsedJSON)
        case .stdout:
            return viewModel.stdout
        case .stderr:
            return viewModel.stderr
        }
    }

    private func prettyJSON(_ dict: [String: AnyHashable]) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: [.prettyPrinted]),
              let str = String(data: data, encoding: .utf8) else {
            return dict.isEmpty ? "(no JSON parsed)" : dict.description
        }
        return str
    }
}
