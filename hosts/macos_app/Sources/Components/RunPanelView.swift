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
                TrackHeaderView(title: mockTrackTitle, badgeText: "Norms Badge")
                    .maSheen(isActive: viewModel.isRunning, duration: 5.5, highlight: Color.white.opacity(0.12))
                DropZoneView { urls in
                    viewModel.enqueue(files: urls)
                    trackVM?.ingestDropped(urls: urls)
                }
                .maCardInteractive()
                HStack(spacing: MAStyle.Spacing.sm) {
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
                CollapsibleSection {
                    HStack {
                        Text("Batch Queue").maText(.headline)
                        Spacer()
                    }
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
                QuickActionsView(actions: quickActions)
                    .maCard()
                SectionsView(sections: sections)
                    .maCard()
                if let trackVM {
                    CollapsibleSection {
                        HStack {
                            Text("Tracks").maText(.headline)
                            Spacer()
                        }
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
                results
                    .maCardInteractive()
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var leftColumn: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            ConsoleView(messages: store.state.messages)
            PromptView(text: Binding(get: { store.state.promptText },
                                     set: { store.dispatch(.setPrompt($0)) }),
                       onSend: sendMessage)
        }
    }

    private var results: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Result").maText(.headline)
            Picker("", selection: Binding(get: { store.state.selectedPane },
                                          set: { store.dispatch(.setPane($0)) })) {
                Text("JSON").tag(ResultPane.json)
                Text("stdout").tag(ResultPane.stdout)
                Text("stderr").tag(ResultPane.stderr)
            }
            .pickerStyle(.segmented)
            .onChange(of: viewModel.parsedJSON, perform: { _ in
                if store.state.selectedPane == .json && viewModel.parsedJSON.isEmpty {
                    store.dispatch(.setPane(.stdout))
                }
            })

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
                        Button("Reveal sidecar") {
                            revealSidecar(path)
                        }
                        .maButton(.ghost)
                        Button("Copy path") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(path, forType: .string)
                        }
                        .maButton(.ghost)
                        Button("Preview sidecar") {
                            viewModel.loadSidecarPreview()
                        }
                        .maButton(.ghost)
                    }
                    Spacer()
                }
            }

            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Copy JSON") {
                    copyJSON()
                }
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

            resultBlock(title: store.state.selectedPane.title,
                        text: paneText(store.state.selectedPane),
                        color: store.state.selectedPane.color)

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
                    .background(color.opacity(0.05))
                    .cornerRadius(MAStyle.Radius.sm)
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

    private func sendMessage() {
        let trimmed = store.state.promptText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        store.dispatch(.appendMessage(trimmed))
        store.dispatch(.setPrompt(""))
    }

    private func loadHistoryPreview(path: String) {
        onPreviewRich(path)
    }
}
