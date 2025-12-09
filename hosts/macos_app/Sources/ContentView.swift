import SwiftUI
import AppKit
import MAStyle
import UniformTypeIdentifiers
import os

struct ContentView: View {
    @StateObject private var store: AppStore
    @ObservedObject private var viewModel: CommandViewModel
    private let trackVM: TrackListViewModel?
    private let previewCacheStore = HistoryPreviewCache()
    private let historyStore = HistoryStore()
    @State private var historyReloadTask: Task<Void, Never>?
    @State private var previewHydrateTask: Task<Void, Never>?
    private let previewLoader = HistoryPreviewLoader()
    @State private var alertTimestamps: [String: Date] = [:]
    @FocusState private var historySearchFocused: Bool
    @FocusState private var promptFocused: Bool
    @State private var showGettingStarted: Bool = true
    @State private var confirmClearHistory: Bool = false
    private let services = AppServices()
    init() {
        let s = AppStore()
        _store = StateObject(wrappedValue: s)
        _viewModel = ObservedObject(wrappedValue: s.commandVM)
        self.trackVM = s.trackVM
    }

    var body: some View {
        ZStack(alignment: .topTrailing) {
            LinearGradient(
                colors: [
                    MAStyle.ColorToken.background,
                    MAStyle.ColorToken.panel.opacity(0.85)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            HStack(spacing: MAStyle.Spacing.md) {
                NavigationRail(
                    selection: Binding(get: { store.state.route.tab },
                                       set: { tab in store.dispatch(.setRoute(store.state.route.updatingTab(tab))) })
                )
                .frame(width: 72)

                Divider()

                VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                    HeaderView(hostStatus: store.state.hostSnapshot.status,
                               progress: store.state.hostSnapshot.processing.progress,
                               showProgress: store.state.hostSnapshot.processing.status == "running",
                               lastUpdated: store.state.hostSnapshot.lastUpdated)
                        .maSheen(isActive: store.commandVM.isRunning, duration: 4.5)
                    SettingsView(useDarkTheme: Binding(get: { store.state.useDarkTheme },
                                                      set: { store.dispatch(.setTheme($0)) }),
                                 statusText: store.commandVM.status)
                    Divider()
                    ScrollView {
                        switch store.state.route.tab {
                        case .run:
                            RunSplitView(
                                store: store,
                                viewModel: viewModel,
                                trackVM: trackVM,
                                pickFile: { services.filePicker.pickFile() },
                                pickDirectory: { services.filePicker.pickDirectory() },
                                revealSidecar: revealSidecar(path:),
                                copyJSON: copyJSON,
                                onPreviewRich: { path in loadHistoryPreview(path: path) }
                            )
                        case .history:
                            HistorySplitView(
                                store: store,
                                reloadHistory: reloadHistory,
                                revealSidecar: revealSidecar(path:),
                                loadPreview: { path in loadHistoryPreview(path: path) },
                                reRun: { item in
                                    guard let path = item?.path else { return }
                                    let fm = FileManager.default
                                    if fm.fileExists(atPath: path) {
                                        viewModel.insertAudioPath(path)
                                    } else {
                                        store.dispatch(.setAlert(AlertHelper.toast("File missing",
                                                                                    message: "Cannot re-run; file not found at \(URL(fileURLWithPath: path).lastPathComponent)",
                                                                                    level: .warning)))
                                    }
                                },
                                historySearchFocus: $historySearchFocused,
                                confirmClearHistory: $confirmClearHistory
                            )
                        case .style:
                            ConsoleTabView(
                                prompt: Binding(get: { store.state.promptText },
                                                set: { store.dispatch(.setPrompt($0)) }),
                                messages: store.state.messages,
                                onSend: sendMessage,
                                onClear: { store.dispatch(.setMessages([])) },
                                onSnippet: { snippet in
                                    store.dispatch(.setPrompt(snippet))
                                    promptFocused = true
                                },
                                promptFocus: $promptFocused
                            )
                        }
                    }
                }
                .padding(MAStyle.Spacing.lg)
                .frame(minWidth: 720, minHeight: 480)
            }

            if let alert = store.state.alert {
                VStack {
                    if alert.presentAsToast {
                        Spacer()
                    }
                    AlertBannerView(alert: alert) {
                        store.dispatch(.setAlert(nil))
                    }
                    .padding(MAStyle.Spacing.md)
                    .transition(.move(edge: alert.presentAsToast ? .bottom : .top).combined(with: .opacity))
                    .zIndex(1)
                }
            }
            if showGettingStarted {
                VStack {
                    GettingStartedOverlay {
                        showGettingStarted = false
                    }
                    .frame(maxWidth: 520)
                    Spacer()
                }
                .padding(MAStyle.Spacing.lg)
                .transition(.opacity)
                .zIndex(2)
            }
        }
        .preferredColorScheme(store.state.useDarkTheme ? .dark : .light)
        .overlay(shortcutButtons.opacity(0))
        .onAppear {
            if store.state.useDarkTheme { MAStyle.useDarkTheme() } else { MAStyle.useLightTheme() }
            reloadHistory()
            hydratePreviewCache()
        }
        .onChange(of: store.state.useDarkTheme) { isDark in
            if isDark { MAStyle.useDarkTheme() } else { MAStyle.useLightTheme() }
        }
        .onReceive(store.commandVM.queueVM.objectWillChange) { _ in
            scheduleHistoryReload()
        }
        .onReceive(store.commandVM.$isRunning) { running in
            let status = running ? "processing" : "idle"
            var snap = store.state.hostSnapshot
            snap.status = status
            snap.lastUpdated = Date()
            store.dispatch(.setHostSnapshot(snap))
        }
        .onChange(of: viewModel.exitCode) { code in
            guard !viewModel.isRunning else { return }
            if code != 0 {
                let message = viewModel.stderr.isEmpty ? viewModel.status : viewModel.stderr
                store.dispatch(.setAlert(AlertState(title: "Run failed (exit \(code))",
                                                    message: message.isEmpty ? "Check console for details." : message,
                                                    level: .error)))
            } else if store.state.alert?.level == .error {
                store.dispatch(.setAlert(nil))
            }
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text("Music Advisor")
                    .maText(.headline)
                Text("SwiftUI shell; configure any local CLI and pipeline.")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            Spacer()
            Text("Live")
                .maBadge(.success)
        }
        .maCard(padding: MAStyle.Spacing.sm)
    }

    private var settings: some View {
        HStack {
            HStack(spacing: MAStyle.Spacing.sm) {
                Text("Theme")
                    .maText(.caption)
                Toggle("", isOn: Binding(get: { store.state.useDarkTheme },
                                         set: { store.dispatch(.setTheme($0)) }))
                    .toggleStyle(.switch)
                    .labelsHidden()
            }
            Spacer()
            if !viewModel.status.isEmpty {
                Text(viewModel.status)
                    .maBadge(.info)
            }
        }
        .maCard(padding: MAStyle.Spacing.sm)
    }

    private var mainSplit: some View {
        HStack(alignment: .top, spacing: MAStyle.Spacing.md) {
            leftColumn
                .frame(maxWidth: 260)
            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                TrackHeaderView(title: store.state.mockTrackTitle, badgeText: "Norms Badge")
                    .maSheen(isActive: viewModel.isRunning, duration: 5.5, highlight: Color.white.opacity(0.12))
                DropZoneView { urls in
                    viewModel.enqueue(files: urls)
                    trackVM?.ingestDropped(urls: urls)
                }
                JobQueueView(
                    jobs: viewModel.queueVM.jobs,
                    onReveal: revealSidecar(path:),
                    onPreviewRich: { richPath in loadHistoryPreview(path: richPath.replacingOccurrences(of: ".client.rich.txt", with: ".json")) },
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
                        if let path = viewModel.sidecarPath { revealSidecar(path: path) }
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

private var historyPane: some View {
    HistoryPanelView(
        items: store.state.historyItems,
        previews: store.state.historyPreviews,
        onRefresh: reloadHistory,
        onReveal: revealSidecar(path:),
        onPreview: { path in
            loadHistoryPreview(path: path)
        },
        onClear: {
            confirmClearHistory = true
        }
    )
    .alert("Clear history?", isPresented: $confirmClearHistory) {
        Button("Cancel", role: .cancel) {}
        Button("Clear", role: .destructive) {
            store.dispatch(.clearHistory)
            try? SpecialActions.clearSidecarsOnDisk()
            reloadHistory()
        }
    } message: {
        Text("This will remove saved sidecars from disk and clear in-memory history.")
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

    private var trackHeader: some View {
        HStack {
            Text(store.state.mockTrackTitle)
                .maText(.headline)
            Spacer()
            Text("Norms Badge")
                .maChip(style: .solid, color: MAStyle.ColorToken.info)
        }
        .maCard()
    }

    private var quickActionsCard: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                Text("Warnings")
                    .maText(.headline)
                Spacer()
            }
            HStack(spacing: MAStyle.Spacing.sm) {
            ForEach(store.state.quickActions, id: \.title) { action in
                    Label(action.title, systemImage: action.symbol)
                        .maChip(style: .outline, color: MAStyle.ColorToken.primary)
                }
                Spacer()
            }
        }
        .maCard()
    }

    private var sectionCards: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            ForEach(store.state.sections, id: \.self) { section in
                HStack {
                    Text(section)
                        .maText(.body)
                    Spacer()
                }
                .maCard(padding: MAStyle.Spacing.sm)
            }
        }
    }

    private var commandInputs: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            if !viewModel.profiles.isEmpty {
                HStack(spacing: MAStyle.Spacing.sm) {
                    Text("Profile").maText(.headline)
                    Picker("Profile", selection: $viewModel.selectedProfile) {
                        ForEach(viewModel.profiles.map { $0.name }, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .labelsHidden()
                    Button("Apply profile") {
                        viewModel.applySelectedProfile()
                    }
                    .maButton(.secondary)
                    .disabled(viewModel.selectedProfile.isEmpty)
                    Button("Reload config") {
                        viewModel.reloadConfig()
                    }
                    .maButton(.ghost)
                    Spacer()
                }
            }

            Text("Command").maText(.headline)
            HStack(spacing: MAStyle.Spacing.sm) {
                TextField("/usr/bin/python3 tools/cli/ma_audio_features.py --audio /path/to/audio.wav --out /tmp/out.json", text: $viewModel.commandText)
                    .textFieldStyle(.roundedBorder)
                    .foregroundColor(.primary)
                Button("Pick audio…") {
                    if let url = pickFile() {
                        viewModel.insertAudioPath(url.path)
                    }
                }
                .maButton(.ghost)
            }

            Text("Working directory (optional)").maText(.headline)
            HStack(spacing: MAStyle.Spacing.sm) {
                TextField("e.g. /Users/you/music-advisor", text: $viewModel.workingDirectory)
                    .textFieldStyle(.roundedBorder)
                    .foregroundColor(.primary)
                Button("Browse…") {
                    if let url = pickDirectory() {
                        viewModel.setWorkingDirectory(url.path)
                    }
                }
                .maButton(.ghost)
            }

            Text("Extra env (KEY=VALUE per line)").maText(.headline)
            TextEditor(text: $viewModel.envText)
                .font(.system(.body, design: .monospaced))
                .foregroundColor(.primary)
                .frame(minHeight: 80)
                .overlay(RoundedRectangle(cornerRadius: MAStyle.Radius.sm).stroke(MAStyle.ColorToken.border))
        }
    }

    private var runButtons: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            Button(action: { viewModel.run() }) {
                if viewModel.isRunning {
                    ProgressView().progressViewStyle(.circular)
                } else {
                    Text("Run CLI")
                }
            }
            .maButton(.primary)
            .disabled(viewModel.isRunning)

            Button("Run defaults") {
                viewModel.loadDefaults()
                viewModel.run()
            }
            .maButton(.secondary)
            .disabled(viewModel.isRunning)

            Button("Run smoke") {
                viewModel.runSmoke()
            }
            .maButton(.ghost)
            .disabled(viewModel.isRunning)

            if !viewModel.status.isEmpty {
                Text(viewModel.status)
                    .font(MAStyle.Typography.body)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                    .maChip(style: .solid, color: MAStyle.ColorToken.info)
            }

            if let last = viewModel.lastRunTime {
                let durationText = viewModel.lastDuration.map { String(format: " (%.2fs)", $0) } ?? ""
                Text("Last run: \(last.formatted(date: .omitted, time: .standard))\(durationText)")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            Spacer()
        }
    }

    private var results: some View {
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
            .onChange(of: viewModel.parsedJSON, perform: { _ in
                if store.state.route.runPane == .json && viewModel.parsedJSON.isEmpty {
                    store.dispatch(.setRoute(store.state.route.updatingRunPane(.stdout)))
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
                            revealSidecar(path: path)
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
        .maCard(padding: MAStyle.Spacing.md)
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
        store.dispatch(.appendMessage("[ack] \(trimmed)"))
    }

    private var shortcutButtons: some View {
        Group {
            Button(action: { historySearchFocused = true }) { EmptyView() }
                .keyboardShortcut("f", modifiers: [.command])
            Button(action: { promptFocused = true }) { EmptyView() }
                .keyboardShortcut("l", modifiers: [.command])
        }
    }

    private func trackStorePaths() -> (trackURL: URL, artistURL: URL) {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let trackURL = appDir.appendingPathComponent("tracks.json")
        let artistURL = appDir.appendingPathComponent("artists.json")
        return (trackURL, artistURL)
    }

    private func makeTrackViewModel() -> TrackListViewModel {
        let paths = trackStorePaths()
        let trackStore = JsonTrackStore(url: paths.trackURL)
        let artistStore = JsonArtistStore(url: paths.artistURL)
        return TrackListViewModel(trackStore: trackStore, artistStore: artistStore)
    }

    private func paneText(_ pane: ResultPane) -> String {
        switch pane {
        case .json:
            return viewModel.parsedJSON.isEmpty ? "(no JSON parsed)" : prettyJSON(viewModel.parsedJSON)
        case .stdout:
            return truncated(viewModel.stdout, label: "stdout")
        case .stderr:
            return truncated(viewModel.stderr, label: "stderr")
        }
    }

    private func truncated(_ text: String, label: String, limit: Int = 8000) -> String {
        guard text.count > limit else { return text }
        let tail = text.suffix(limit)
        return "[\(label) truncated to last \(limit) chars]\n\(tail)"
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}

// MARK: - Pickers
extension ContentView {
    private func pickFile() -> URL? {
        services.filePicker.pickFile()
    }

    private func pickDirectory() -> URL? {
        services.filePicker.pickDirectory()
    }

    private func revealSidecar(path: String) {
        let url = URL(fileURLWithPath: path)
        guard FileManager.default.fileExists(atPath: url.path) else {
            store.dispatch(.setAlert(AlertHelper.toast("File missing", message: "Sidecar not found at \(url.lastPathComponent)", level: .warning)))
            return
        }
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }

    private func copyJSON() {
        let jsonString = viewModel.parsedJSON.isEmpty ? "" : prettyJSON(viewModel.parsedJSON)
        guard !jsonString.isEmpty else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(jsonString, forType: .string)
    }

    private func applyTheme(_ isDark: Bool) {
        if isDark {
            MAStyle.useDarkTheme()
        } else {
            MAStyle.useLightTheme()
        }
    }

    private func reloadHistory() {
        historyReloadTask?.cancel()
        historyReloadTask = Task(priority: .utility) { await reloadHistoryAsync() }
    }

    private func reloadHistoryAsync() async {
        let signpostID = Perf.begin(Perf.historyLog, "history.reload")
        let fm = FileManager.default
        let supportDir = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let sidecarDir = supportDir.appendingPathComponent("MusicAdvisorMacApp/sidecars", isDirectory: true)
        if let urls = try? fm.contentsOfDirectory(at: sidecarDir,
                                                  includingPropertiesForKeys: [.contentModificationDateKey],
                                                  options: [.skipsHiddenFiles]) {
            let items: [SidecarItem] = urls.compactMap { url in
                let attrs = try? url.resourceValues(forKeys: [.contentModificationDateKey])
                let mod = attrs?.contentModificationDate ?? Date.distantPast
                return SidecarItem(path: url.path, name: url.lastPathComponent, modified: mod)
            }
            let sorted = items.sorted { $0.modified > $1.modified }
            await MainActor.run {
                store.dispatch(.setHistoryItems(sorted))
                historyStore.save(sorted)
            }
            Perf.end(Perf.historyLog, "history.reload", signpostID)
            return
        }

        // Fallback to cached history if sidecar directory is missing.
        let (persisted, _) = await historyStore.loadAsync(filterExisting: true)
        await MainActor.run {
            store.dispatch(.setHistoryItems(persisted))
            store.dispatch(.setAlert(AlertHelper.toast("History load",
                                                       message: "Could not read sidecars directory; using cached history if available.",
                                                       level: .warning)))
        }
        Perf.end(Perf.historyLog, "history.reload", signpostID)
    }

    private func scheduleHistoryReload() {
        historyReloadTask?.cancel()
        historyReloadTask = Task(priority: .utility) {
            try? await Task.sleep(nanoseconds: 350_000_000)
            await reloadHistoryAsync()
        }
    }

    private func hydratePreviewCache() {
        previewHydrateTask?.cancel()
        previewHydrateTask = Task.detached(priority: .utility) {
            let cached = await previewCacheStore.loadAsync(filterExisting: true)
            guard !cached.isEmpty else { return }
            await MainActor.run {
                store.state.previewCache = cached
                for (path, preview) in cached {
                    store.dispatch(.setHistoryPreview(path: path, preview: preview.0))
                }
            }
        }
    }

    private func loadHistoryPreview(path: String) {
        if let cached = store.state.previewCache[path] {
            store.dispatch(.setHistoryPreview(path: path, preview: cached.0))
            return
        }
        Task {
            let signpostID = Perf.begin(Perf.previewLog, "preview.load")
            let (preview, mtime, unreadable, missingRich) = await previewLoader.load(path: path)
            await MainActor.run {
                store.dispatch(.setPreviewCache(path: path, preview: preview))
                store.dispatch(.setHistoryPreview(path: path, preview: preview))
                var cache = store.state.previewCache
                cache[path] = (preview, mtime)
                store.state.previewCache = cache
                previewCacheStore.save(cache)

                if unreadable {
                    showAlertThrottled(key: "preview_unreadable",
                                       alert: AlertHelper.toast("Preview unreadable",
                                                                message: "Could not read sidecar at \(path)",
                                                                level: .warning))
                } else if missingRich {
                    showAlertThrottled(key: "preview_missing_rich",
                                       alert: AlertHelper.toast("Rich preview missing",
                                                                message: "No .client.rich.txt found for \(URL(fileURLWithPath: path).lastPathComponent)",
                                                                level: .info))
                }

                var prunedCache = store.state.previewCache
                for key in prunedCache.keys {
                    if !FileManager.default.fileExists(atPath: key) {
                        prunedCache.removeValue(forKey: key)
                    }
                }
                store.state.previewCache = prunedCache
                previewCacheStore.save(prunedCache)

                let existingHistory = store.state.historyItems.filter { FileManager.default.fileExists(atPath: $0.path) }
                if existingHistory.count != store.state.historyItems.count {
                    store.dispatch(.setHistoryItems(existingHistory))
                    historyStore.save(existingHistory)
                }
                showAlertThrottled(key: "preview_done", alert: AlertHelper.toast("Preview updated", message: selectedPreviewName(path), level: .info))
            }
            Perf.end(Perf.previewLog, "preview.load", signpostID)
        }
    }

    @MainActor
    private func showAlertThrottled(key: String, alert: AlertState, minInterval: TimeInterval = 1.2) {
        let now = Date()
        if let last = alertTimestamps[key], now.timeIntervalSince(last) < minInterval {
            return
        }
        alertTimestamps[key] = now
        store.dispatch(.setAlert(alert))
    }

    private func selectedPreviewName(_ path: String) -> String {
        URL(fileURLWithPath: path).lastPathComponent
    }
}
