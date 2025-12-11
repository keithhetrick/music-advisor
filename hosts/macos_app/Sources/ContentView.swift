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
    private let chatProvider: ChatProvider = ChatService()
    @State private var alertTimestamps: [String: Date] = [:]
    @FocusState private var historySearchFocused: Bool
    @FocusState private var promptFocused: Bool
    @State private var showGettingStarted: Bool = false
    @State private var confirmClearHistory: Bool = false
    private let services = AppServices()
    @State private var chatIsThinking: Bool = false
    @State private var chatTask: Task<Void, Never>?
    @State private var contextLastUpdated: Date? = nil
    @State private var showChatOverlay: Bool = false
    @State private var pendingChatCard: PlaybookCard? = nil
    @State private var canRun: Bool = true
    @State private var disabledReason: String? = nil
    @State private var runWarnings: [String] = []
    @State private var missingAudioWarning: String? = nil
    @State private var showSettingsSheet: Bool = false
    init() {
        let s = AppStore()
        _store = StateObject(wrappedValue: s)
        _viewModel = ObservedObject(wrappedValue: s.commandVM)
        self.trackVM = s.trackVM
    }

    private func handleRunDrop(providers: [NSItemProvider]) -> Bool {
        var handled = false
        for provider in providers {
            if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) ||
                provider.hasItemConformingToTypeIdentifier(UTType.audio.identifier) {
                handled = true
                provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                    if let data = item as? Data,
                       let url = URL(dataRepresentation: data, relativeTo: nil) {
                        Task { @MainActor in
                            store.enqueueFromDrop([url], baseCommand: viewModel.commandText)
                            trackVM?.ingestDropped(urls: [url])
                        }
                    }
                }
            }
        }
        return handled
    }

    var body: some View {
        ZStack(alignment: .topTrailing) {
            MAStyle.Backdrop(intensity: 1.0, accent: MAStyle.ColorToken.primary)
                .ignoresSafeArea()

            HStack(spacing: MAStyle.Spacing.md) {
                NavigationRail(
                    selection: Binding(get: { store.state.route.tab },
                                       set: { tab in
                                           showSettingsSheet = false
                                           store.dispatch(.setRoute(store.state.route.updatingTab(tab)))
                                       }),
                    isDarkTheme: store.state.useDarkTheme,
                    followSystemTheme: store.state.followSystemTheme,
                    onToggleTheme: {
                        let systemDark = MAStyle.systemPrefersDark()
                        if store.state.followSystemTheme {
                            // Switch to manual using current system appearance.
                            store.dispatch(.setFollowSystemTheme(false))
                            let applied = MAStyle.applyTheme(followSystem: false, manualDark: systemDark)
                            store.dispatch(.setTheme(applied))
                        } else {
                            let newValue = !store.state.useDarkTheme
                            let applied = MAStyle.applyTheme(followSystem: false, manualDark: newValue)
                            store.dispatch(.setTheme(applied))
                        }
                    },
                    onSettings: { showSettingsSheet = true }
                )

                VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                    HeaderView(hostStatus: store.state.hostSnapshot.status,
                               progress: store.state.hostSnapshot.processing.progress,
                               showProgress: store.state.hostSnapshot.processing.status == "running",
                               lastUpdated: store.state.hostSnapshot.lastUpdated)
                        .maSheen(isActive: store.commandVM.isRunning, duration: 4.5)
                    HStack {
                        Text(tabTitle(for: store.state.route.tab))
                            .maText(.headline)
                        Spacer()
                    }
                    Divider()
                    ScrollView(.vertical) {
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
                        onPreviewRich: { path in loadHistoryPreview(path: path) },
                        canRun: canRun,
                        disabledReason: disabledReason,
                        runWarnings: runWarnings,
                        missingAudioWarning: missingAudioWarning,
                        onPickAudio: {
                            services.filePicker.pickFile().map { url in
                                viewModel.insertAudioPath(url.path)
                                return url
                            }
                        },
                        onShowHistory: {
                            store.dispatch(.setRoute(store.state.route.updatingTab(.history)))
                        }
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
                onSelectContext: { path in
                    setChatContext(selection: "history", overridePath: path)
                },
                                historySearchFocus: $historySearchFocused,
                                confirmClearHistory: $confirmClearHistory
                            )
                        case .style:
                            PlaybookView(
                                references: referenceOptions(),
                                onAnalyze: { card, ref in
                                    let result = analyzePlaybook(card: card, reference: ref)
                                    return result
                                },
                                onAskChat: { card, ref, context in
                                    openChat(for: card, mode: .ask, reference: ref, context: context)
                                }
                            )
                        }
                    }
                    .padding(.horizontal, MAStyle.Spacing.md)
                }
                .padding(MAStyle.Spacing.md)
                .frame(minWidth: 720, minHeight: 480, alignment: .top)
            }
            .padding(.horizontal, MAStyle.Spacing.md)
            .padding(.vertical, MAStyle.Spacing.md)

            if let alert = store.state.alert {
                VStack {
                    if alert.presentAsToast { Spacer() }
                    AlertBanner(
                        title: alert.title,
                        message: alert.message,
                        tone: mapTone(alert.level),
                        presentAsToast: alert.presentAsToast,
                        onClose: { store.dispatch(.setAlert(nil)) }
                    )
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
        .preferredColorScheme(store.state.followSystemTheme ? nil : (store.state.useDarkTheme ? .dark : .light))
        .overlay(shortcutButtons.opacity(0))
        .overlay {
            if showSettingsSheet {
                ZStack {
                    Color.black.opacity(0.35)
                        .ignoresSafeArea()
                        .onTapGesture { showSettingsSheet = false }
                    SettingsSheet(
                        useDarkTheme: Binding(get: { store.state.useDarkTheme },
                                              set: { value in
                                                  store.dispatch(.setFollowSystemTheme(false))
                                                  store.dispatch(.setTheme(value))
                                                  if value { MAStyle.useDarkTheme() } else { MAStyle.useLightTheme() }
                                              }),
                        statusText: store.commandVM.status,
                        dataPath: applicationSupportPath(),
                        onClose: { showSettingsSheet = false },
                        uiTestMode: store.isUITestHarnessActive
                    )
                    .frame(width: 320)
                    .padding(MAStyle.Spacing.sm)
                    .maHoverLift(enabled: false)
                    .accessibilityIdentifier("settings-overlay")
                }
                .maModalTransition()
                .zIndex(3)
            }
        }
        .overlay {
            if showChatOverlay {
                ZStack {
                    Color.black.opacity(0.35)
                        .ignoresSafeArea()
                        .onTapGesture { showChatOverlay = false }
                    VStack(spacing: 0) {
                        HStack(spacing: MAStyle.Spacing.sm) {
                            Text("Chat")
                                .maText(.headline)
                                .foregroundStyle(MAStyle.ColorToken.muted)
                            Spacer()
                            Button {
                                showChatOverlay = false
                            } label: {
                                Image(systemName: "xmark")
                                    .font(.system(size: 12, weight: .bold))
                                    .padding(6)
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("Close chat")
                        }
                        .padding(.horizontal, MAStyle.Spacing.md)
                        .padding(.vertical, MAStyle.Spacing.sm)
                        .background(MAStyle.ColorToken.panel.opacity(0.9))
                        .overlay(alignment: .bottom) {
                            Divider()
                                .foregroundStyle(MAStyle.ColorToken.border)
                        }
                        ConsoleTabView(
                            prompt: Binding(get: { store.state.promptText },
                                            set: { store.dispatch(.setPrompt($0)) }),
                            messages: store.state.messages,
                            onSend: sendMessage,
                            onClear: { store.dispatch(.setMessages([])) },
                            onSnippet: { snippet in
                                store.dispatch(.setPrompt(snippet))
                                promptFocused = true
                                if let last = viewModel.sidecarPath {
                                    setChatContext(selection: "last-run", overridePath: last)
                                }
                            },
                            onStop: stopChat,
                            onDevSmoke: runChatEngineSmoke,
                            promptFocus: $promptFocused,
                            isThinking: chatIsThinking,
                            contextOptions: chatContextOptions(),
                            selectedContext: chatSelectionBinding(),
                            contextLabel: store.state.chatContextLabel,
                            contextBadgeTitle: store.state.chatBadgeTitle,
                            contextBadgeSubtitle: store.state.chatBadgeSubtitle,
                            contextLastUpdated: store.state.chatContextLastUpdated
                        )
                        .frame(minWidth: 480, maxWidth: 720, minHeight: 360, maxHeight: 600)
                        .padding(.horizontal)
                        .padding(.bottom)
                        .maHoverLift(enabled: false)
                    }
                    .background(MAStyle.ColorToken.panel)
                    .cornerRadius(MAStyle.Radius.lg)
                    .shadow(color: .black.opacity(0.3), radius: 14, x: 0, y: 8)
                }
                .maModalTransition()
                .zIndex(3)
            }
        }
        .overlay(alignment: .topTrailing) {
            if store.isUITestHarnessActive {
                VStack(alignment: .trailing, spacing: MAStyle.Spacing.xs) {
                    Button("Start UI test queue") {
                        store.startQueue()
                    }
                    .maButton(.secondary)
                    .accessibilityIdentifier("ui-test-start-queue")

                    Button("Reset UI test queue") {
                        store.seedQueueForUITests()
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-reset-queue")

                    Button("Show test toast") {
                        store.dispatch(.setAlert(AlertHelper.toast("UI Test Toast", message: "Debug toast for UI automation", level: .info)))
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-show-toast")

                    Button("Stop UI test queue") {
                        store.stopQueue()
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-stop-queue")

                    Button("Open settings") {
                        showSettingsSheet = true
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-open-settings")

                    Button("Enqueue sample job") {
                        store.enqueueSampleJobForUITests()
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-enqueue-sample")

                    Button("Make pending jobs canceled") {
                        store.forceCanceledForUITests()
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-make-canceled")

                    Button("Show resume control") {
                        store.ensureResumeAvailableForUITests()
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-show-resume")

                    Button("Expand folders") {
                        NotificationCenter.default.post(name: .uiTestExpandFolders, object: nil)
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-expand-folders")

                    Button("Force resume canceled") {
                        store.forceResumeCanceledForUITests()
                    }
                    .maButton(.ghost)
                    .accessibilityIdentifier("ui-test-force-resume")
                }
                .padding(MAStyle.Spacing.md)
            }
        }
        .onAppear {
            // Ensure the app becomes frontmost so text input goes to the window, not the launching terminal.
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                NSApplication.shared.activate(ignoringOtherApps: true)
            }
            let effectiveDark = MAStyle.applyTheme(followSystem: store.state.followSystemTheme,
                                                   manualDark: store.state.useDarkTheme)
            store.dispatch(.setTheme(effectiveDark))
            reloadHistory()
            hydratePreviewCache()
        }
        .onChange(of: store.state.useDarkTheme) { isDark in
            guard !store.state.followSystemTheme else { return }
            MAStyle.applyTheme(followSystem: false, manualDark: isDark)
        }
        .onChange(of: store.state.followSystemTheme) { follow in
            let effectiveDark = MAStyle.applyTheme(followSystem: follow,
                                                   manualDark: store.state.useDarkTheme)
            store.dispatch(.setTheme(effectiveDark))
        }
        .onReceive(store.commandVM.queueVM.objectWillChange) { _ in
            scheduleHistoryReload()
        }
        .onReceive(MAStyle.appearanceChangePublisher()) { systemDark in
            guard store.state.followSystemTheme else { return }
            store.dispatch(.setTheme(systemDark))
            MAStyle.applyTheme(followSystem: true, manualDark: store.state.useDarkTheme)
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
        .onChange(of: viewModel.sidecarPath) { _ in
            // Default to the latest run sidecar when available.
            if viewModel.sidecarPath != nil {
                setChatContext(selection: "last-run", overridePath: viewModel.sidecarPath)
                contextLastUpdated = Date()
            }
        }
        .onChange(of: store.state.chatSelection) { newSel in
            renderChatContext(selection: newSel, overridePath: store.state.chatOverridePath)
            contextLastUpdated = Date()
            showSettingsSheet = false
        }
        .onChange(of: store.state.chatOverridePath) { newOverride in
            renderChatContext(selection: store.state.chatSelection, overridePath: newOverride)
            contextLastUpdated = Date()
        }
        .onChange(of: store.state.route.tab) { _ in
            showSettingsSheet = false
        }
        .onAppear {
            renderChatContext(selection: store.state.chatSelection, overridePath: store.state.chatOverridePath)
            refreshRunReadiness()
        }
        .onChange(of: viewModel.commandText) { _ in refreshRunReadiness() }
        .onChange(of: viewModel.queueVM.jobs) { _ in refreshRunReadiness() }
    }

    // MARK: - Drop handling
    // Drop handling is scoped to DropZoneView to avoid blocking scroll/gestures.

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
                    store.enqueueFromDrop(urls, baseCommand: viewModel.commandText)
                }
                JobQueueView(
                    jobs: store.state.queueJobs,
                    ingestPendingCount: store.state.ingestPendingCount,
                    ingestErrorCount: store.state.ingestErrorCount,
                    onReveal: revealSidecar(path:),
                    onPreviewRich: { richPath in loadHistoryPreview(path: richPath.replacingOccurrences(of: ".client.rich.txt", with: ".json")) },
                    onClear: {
                        store.clearQueueAll()
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
            PromptBar(
                text: Binding(get: { store.state.promptText },
                              set: { store.dispatch(.setPrompt($0)) }),
                placeholder: "Type a message…",
                isThinking: chatIsThinking,
                focus: $promptFocused,
                onSend: sendMessage,
                onClear: { store.dispatch(.setPrompt("")) }
            )
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
        let prompt = store.state.promptText
        guard !prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        store.dispatch(.setPrompt(""))
        chatTask?.cancel()
        chatIsThinking = true
        let selection = store.state.chatSelection
        let sidecarPath = viewModel.sidecarPath
        let overridePath = store.state.chatOverridePath
        let historyItems = store.state.historyItems
        let previewCache = store.state.previewCache

        var effectiveSelection = selection
        var effectiveOverride = overridePath

        // Best effort badge before send.
        updateBadge(label: contextLabelForSelection(effectiveSelection),
                    path: effectiveOverride ?? sidecarPath)

        // Fallback: if prompt itself is an absolute .client.rich.txt path, use it.
        if let pathFromPrompt = absoluteRichPath(from: prompt) {
            effectiveOverride = pathFromPrompt
            effectiveSelection = "manual-path"
            setChatContext(selection: effectiveSelection, overridePath: effectiveOverride)
            showAlertThrottled(key: "chat_manual_ctx", alert: AlertHelper.toast("Context from prompt",
                                                                                message: "Using \(URL(fileURLWithPath: pathFromPrompt).lastPathComponent)",
                                                                                level: .info))
        }

        chatTask = Task {
            await performChat(prompt: prompt,
                              selection: effectiveSelection,
                              overridePath: effectiveOverride,
                              sidecarPath: sidecarPath,
                              historyItems: historyItems,
                              previewCache: previewCache)
        }
    }

    private func chatSelectionBinding() -> Binding<String?> {
        Binding(get: { store.state.chatSelection },
                set: { newValue in
                    setChatContext(selection: newValue, overridePath: store.state.chatOverridePath)
                })
    }

    private func chatContextOptions() -> [ChatContextOption] {
        var opts: [ChatContextOption] = [
            ChatContextOption(id: "none", label: "No context", path: nil)
        ]
        if let path = viewModel.sidecarPath {
            opts.append(ChatContextOption(id: "last-run", label: "Last run", path: path))
        }
        if let path = store.state.chatOverridePath {
            opts.append(ChatContextOption(id: "history", label: "History preview", path: path))
        }
        if !store.state.historyItems.isEmpty {
            let historyOpts = store.state.historyItems.prefix(10).map {
                ChatContextOption(id: "hist-\($0.id.uuidString)",
                                  label: "History: \($0.name)",
                                  path: $0.path)
            }
            opts.append(contentsOf: historyOpts)
        }
        return opts
    }

    private func setChatContext(selection: String?, overridePath: String?) {
        store.dispatch(.setChatSelection(selection))
        store.dispatch(.setChatOverride(overridePath))
        renderChatContext(selection: selection, overridePath: overridePath)
    }

    private func renderChatContext(selection: String?, overridePath: String?) {
        updateBadge(label: contextLabelForSelection(selection),
                    path: overridePath ?? viewModel.sidecarPath)
    }

    private func contextLabelForSelection(_ sel: String?) -> String {
        guard let sel else { return "No context" }
        let opts = chatContextOptions()
        if let match = opts.first(where: { $0.id == sel }) {
            return match.label
        }
        switch sel {
        case "last-run": return "Last run"
        case "history": return "History preview"
        case "manual-path": return "Manual path"
        default: return "No context"
        }
    }

    private func stopChat() {
        chatTask?.cancel()
        chatIsThinking = false
    }

    private func absoluteRichPath(from prompt: String) -> String? {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("/") else { return nil }
        guard trimmed.hasSuffix(".client.rich.txt") else { return nil }
        if FileManager.default.fileExists(atPath: trimmed) {
            return trimmed
        }
        return nil
    }

    private func updateBadge(label: String?, path: String?) {
        let title = label ?? "No context"
        var subtitle = "No file"
        if let path, FileManager.default.fileExists(atPath: path) {
            subtitle = URL(fileURLWithPath: path).lastPathComponent
            store.dispatch(.setChatContextPath(path))
        } else {
            store.dispatch(.setChatContextPath(nil))
        }
        store.dispatch(.setChatContextLabel(title))
        store.dispatch(.setChatBadge(title: title, subtitle: subtitle))
        store.dispatch(.setChatContextTimestamp(Date()))
    }

    private func performChat(prompt: String,
                             selection: String?,
                             overridePath: String?,
                             sidecarPath: String?,
                             historyItems: [SidecarItem],
                             previewCache: [String: (HistoryPreview, Date?)]) async {
        let ctx = ChatContext(selection: selection,
                              sidecarPath: sidecarPath,
                              overridePath: overridePath,
                              historyItems: historyItems,
                              previewCache: previewCache)
        let result = await chatProvider.send(prompt: prompt,
                                             context: ctx,
                                             lastSent: nil)
        guard !Task.isCancelled else { return }
        handleChatResult(result: result, prompt: prompt)
    }

    @MainActor
    private func handleChatResult(result: (reply: String?, rateLimited: Bool, timedOut: Bool, warning: String?, label: String, contextPath: String?, nextSentAt: Date?), prompt: String) {
        chatIsThinking = false
        if result.rateLimited {
            showAlertThrottled(key: "chat_rate", alert: AlertHelper.toast("Slow down", message: "Please wait a moment between sends.", level: .info))
            return
        }
        if let warn = result.warning {
            showAlertThrottled(key: "chat_context_warn", alert: AlertHelper.toast("Context", message: warn, level: .warning))
        }
        let outgoingContext = result.label
        store.dispatch(.appendMessage(prompt))
        if let reply = result.reply, !reply.isEmpty {
            store.dispatch(.appendMessage(reply))
            if result.timedOut || reply.contains("chat error") {
                store.dispatch(.setAlert(AlertHelper.toast("Chat issue", message: reply, level: .warning)))
            }
        }
        updateBadge(label: outgoingContext, path: result.contextPath)
    }

    private func runChatEngineSmoke() {
        Task {
            let path = store.state.chatOverridePath ?? viewModel.sidecarPath
            let res = await ChatEngineSmoke.run(prompt: store.state.promptText.isEmpty ? "Hello" : store.state.promptText,
                                                contextPath: path)
            let msg = res.reply ?? "(no reply)"
            let title = res.exit == 0 ? "Chat engine smoke" : "Chat engine smoke (error)"
            let level: AlertState.Level = res.exit == 0 ? .info : .error
            store.dispatch(.setAlert(AlertHelper.toast(title, message: msg, level: level)))
        }
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

    private var railHiddenPadding: CGFloat { MAStyle.Spacing.md }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}

// MARK: - Helpers
extension ContentView {
    fileprivate func mapTone(_ level: AlertState.Level) -> AlertBanner.Tone {
        switch level {
        case .info: return .info
        case .warning: return .warning
        case .error: return .error
        }
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
            // Set chat context to this history item when previewed.
            setChatContext(selection: "history", overridePath: cached.0.richPath ?? path)
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
                setChatContext(selection: "history", overridePath: preview.richPath ?? path)

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

    private func applicationSupportPath() -> String? {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
        return supportDir?.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true).path
    }

    private func refreshRunReadiness() {
        let hasCommand = !viewModel.commandText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        let hasPending = viewModel.queueVM.jobs.contains { $0.status == .pending || $0.status == .running }
        canRun = hasCommand || hasPending
        var warnings: [String] = []
        if viewModel.workingDirectory.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            warnings.append("Working directory not set.")
        } else if !FileManager.default.fileExists(atPath: viewModel.workingDirectory) {
            warnings.append("Working directory is missing.")
        }
        if !viewModel.commandText.contains("--audio") && !hasPending {
            missingAudioWarning = "Audio argument not set; enqueue files or add --audio."
        } else {
            missingAudioWarning = nil
        }
        if !hasCommand && !hasPending {
            disabledReason = "Provide a command or enqueue files first."
        } else {
            disabledReason = nil
        }
        runWarnings = warnings
    }

    private enum ChatMode {
        case analyze
        case ask
    }

    private func openChat(for card: PlaybookCard, mode: ChatMode, reference: String? = nil, context: String? = nil) {
        let baseContext = context ?? playbookContextSummary(reference: reference)
        let prompt: String
        switch mode {
        case .analyze:
            prompt = "Analyze goal: \(card.title). Context: \(baseContext)"
        case .ask:
            prompt = "Question about \(card.title). Context: \(baseContext)"
        }
        store.dispatch(.setPrompt(prompt))
        pendingChatCard = card
        showChatOverlay = true
    }

    private func analyzePlaybook(card: PlaybookCard, reference: String?) -> PlaybookResult {
        let metricsSummary = viewModel.summaryMetrics.map { "\($0.label): \($0.value)" }.joined(separator: ", ")
        let exit = viewModel.exitCode
        var issues: [String] = []
        var fixes: [String] = []
        var impact: [String] = []
        if exit != 0 {
            issues.append("Last run failed (exit \(exit)).")
            fixes.append("Inspect stderr and rerun after resolving errors.")
        }
        if metricsSummary.isEmpty {
            issues.append("No metrics parsed from last run.")
            fixes.append("Ensure JSON output contains summary metrics.")
        } else {
            impact.append("Current metrics: \(metricsSummary)")
        }
        if let reference {
            impact.append("Reference: \(reference)")
            fixes.append("Compare current metrics against reference and align LUFS/tempo/key.")
        }
        let context = playbookContextSummary(reference: reference)
        return PlaybookResult(issues: issues, fixes: fixes, impact: impact, contextSummary: context)
    }

    private func playbookContextSummary(reference: String?) -> String {
        let metricsSummary = viewModel.summaryMetrics.map { "\($0.label): \($0.value)" }.joined(separator: ", ")
        let sidecar = viewModel.sidecarPath ?? "n/a"
        var parts: [String] = []
        if !metricsSummary.isEmpty { parts.append("Metrics: \(metricsSummary)") }
        parts.append("Sidecar: \(sidecar)")
        if let reference { parts.append("Reference: \(reference)") }
        return parts.joined(separator: " | ")
    }

    private func referenceOptions() -> [String] {
        store.state.historyItems.prefix(8).map { $0.name }
    }

    private func tabTitle(for tab: AppTab) -> String {
        switch tab {
        case .run: return "Run"
        case .history: return "History"
        case .style: return "Playbook"
        }
    }
}
