import SwiftUI
import AppKit
import MAStyle
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
    @State private var historyLoading: Bool = false
    @State private var showPalette: Bool = false
    @State private var paletteQuery: String = ""
    private let echoEnabled: Bool = ProcessInfo.processInfo.environment["MA_ECHO_BROKER_ENABLE"] == "1"
    init() {
        let s = AppStore()
        _store = StateObject(wrappedValue: s)
        _viewModel = ObservedObject(wrappedValue: s.commandVM)
        self.trackVM = s.trackVM
    }

    var body: some View {
        ZStack(alignment: .topTrailing) {
            LinearGradient(colors: DesignTokens.Gradient.backdrop,
                           startPoint: .topLeading,
                           endPoint: .bottomTrailing)
                .ignoresSafeArea()

            HStack(spacing: DesignTokens.Spacing.md) {
                sidebar
                Divider()
                    .padding(.vertical, DesignTokens.Spacing.lg)
                mainScaffold
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.vertical, DesignTokens.Spacing.lg)

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
                    .padding(DesignTokens.Spacing.md)
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
                .padding(DesignTokens.Spacing.lg)
                .transition(.opacity)
                .zIndex(2)
            }
        }
        .preferredColorScheme(store.state.followSystemTheme ? nil : (store.state.useDarkTheme ? .dark : .light))
        .overlay(shortcutButtons.opacity(0))
        .overlay {
            if showPalette {
                CommandPalette(isPresented: $showPalette,
                               query: $paletteQuery,
                               entries: paletteEntries())
                .zIndex(4)
            }
        }
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
                            Text("Guide")
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
                        .frame(minWidth: 520, maxWidth: 760, minHeight: 360, maxHeight: 620)
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

    // MARK: - Shell layout

    private var sidebar: some View {
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
                    // Switch to manual and invert current system to make change visible.
                    store.dispatch(.setFollowSystemTheme(false))
                    let newValue = !systemDark
                    store.dispatch(.setTheme(newValue))
                    _ = MAStyle.applyTheme(followSystem: false, manualDark: newValue)
                } else {
                    let newValue = !store.state.useDarkTheme
                    store.dispatch(.setTheme(newValue))
                    _ = MAStyle.applyTheme(followSystem: false, manualDark: newValue)
                }
            },
            onSettings: { showSettingsSheet = true }
        )
        .frame(maxHeight: .infinity, alignment: .top)
        .padding(.vertical, DesignTokens.Spacing.sm)
    }

    private var mainScaffold: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            headerBar
            if store.state.route.tab == .results, (viewModel.sidecarPath != nil || !viewModel.summaryMetrics.isEmpty) {
                contextRibbon
            }
            ScrollView(.vertical) {
                detailContent
                    .padding(.bottom, DesignTokens.Spacing.lg)
            }
        }
        .frame(minWidth: 960, minHeight: 560, alignment: .topLeading)
    }

    private var headerBar: some View {
        HStack(alignment: .center, spacing: DesignTokens.Spacing.sm) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text(tabTitle(for: store.state.route.tab))
                    .font(DesignTokens.Typography.title)
                Text(routeSubtitle(for: store.state.route.tab))
                    .font(DesignTokens.Typography.caption)
                    .foregroundStyle(DesignTokens.Color.muted)
            }
            Spacer()
            HStack(spacing: DesignTokens.Spacing.sm) {
                VStack(alignment: .trailing, spacing: DesignTokens.Spacing.xs) {
                    Text(store.state.hostSnapshot.status.capitalized)
                        .maBadge(store.commandVM.isRunning ? .warning : .info)
                    if store.state.hostSnapshot.processing.status == "running" {
                        ProgressView(value: store.state.hostSnapshot.processing.progress)
                            .frame(width: 120)
                            .maProgressStyle()
                    }
                    if let last = store.state.hostSnapshot.lastUpdated {
                        let rel = RelativeDateTimeFormatter().localizedString(for: last, relativeTo: Date())
                        Text("Updated \(rel)")
                            .maText(.caption)
                            .foregroundStyle(DesignTokens.Color.muted)
                    }
                }
                Divider()
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text(store.state.chatBadgeTitle)
                        .maText(.body)
                    Text(store.state.chatBadgeSubtitle)
                        .maText(.caption)
                        .foregroundStyle(DesignTokens.Color.muted)
                    HStack(spacing: DesignTokens.Spacing.xs) {
                        Button {
                            setChatContext(selection: "last-run", overridePath: viewModel.sidecarPath)
                            showChatOverlay = true
                        } label: {
                            Label("Guide", systemImage: "bubble.left.and.bubble.right")
                        }
                        .maButton(.secondary)
                        Button {
                            store.dispatch(.setShowAdvanced(!store.state.showAdvanced))
                        } label: {
                            Image(systemName: store.state.showAdvanced ? "sidebar.trailing" : "sidebar.right")
                                .font(.system(size: 13, weight: .medium))
                        }
                        .maButton(.ghost)
                        .help("Toggle inspector")
                    }
                }
            }
        }
        .cardSurface(padding: DesignTokens.Spacing.xs, cornerRadius: DesignTokens.Radius.lg)
        .frame(maxHeight: 110)
    }

    @ViewBuilder
    private var detailContent: some View {
        switch store.state.route.tab {
        case .library:
            libraryView
        case .analyze:
            analyzeView
        case .results:
            resultsDashboard
        case .echo:
            echoView
        case .guide:
            guidePanel
        case .settings:
            settingsPanel
        }
    }

    private var libraryView: some View {
        VStack(spacing: DesignTokens.Spacing.md) {
            HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
                quickStartCard
                    .frame(maxWidth: 380)
                VStack(spacing: DesignTokens.Spacing.md) {
                    historyPeekCard
                    latestResultCard
                }
            }
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
                confirmClearHistory: $confirmClearHistory,
                isLoading: historyLoading
            )
            .cardSurface(padding: DesignTokens.Spacing.sm, cornerRadius: DesignTokens.Radius.lg, shadow: DesignTokens.Shadow.subtle)
        }
        .padding(.trailing, DesignTokens.Spacing.md)
    }

    private var quickStartCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Import a track")
                .font(DesignTokens.Typography.headline)
            Text("Drop or pick audio to queue it instantly. Analysis runs in the Analyze tab.")
                .font(DesignTokens.Typography.caption)
                .foregroundStyle(DesignTokens.Color.muted)
            HStack(spacing: DesignTokens.Spacing.sm) {
                Button {
                    if let url = services.filePicker.pickFile() {
                        viewModel.insertAudioPath(url.path)
                        trackVM?.ingestDropped(urls: [url])
                        store.dispatch(.setRoute(.analyze(store.state.route.runPane)))
                    }
                } label: {
                    Label("Import audio", systemImage: "square.and.arrow.down")
                }
                .maButton(.primary)
                Button {
                    services.filePicker.pickDirectory().map { url in
                        viewModel.setWorkingDirectory(url.path)
                    }
                } label: {
                    Label("Set working directory", systemImage: "folder")
                }
                .maButton(.ghost)
            }
            DropZoneView { urls in
                store.enqueueFromDrop(urls, baseCommand: viewModel.commandText)
                trackVM?.ingestDropped(urls: urls)
            }
            .frame(height: 120)
            .cardSurface(padding: DesignTokens.Spacing.sm, cornerRadius: DesignTokens.Radius.md, shadow: DesignTokens.Shadow.subtle)
        }
        .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg, shadow: DesignTokens.Shadow.medium)
    }

    private var historyPeekCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text("Recent sidecars")
                    .font(DesignTokens.Typography.headline)
                Spacer()
                Button("Refresh", action: reloadHistory)
                    .maButton(.ghost)
            }
            let recent = store.state.historyItems.prefix(3)
            if historyLoading {
                ForEach(0..<3) { _ in
                    SkeletonView(height: 48, cornerRadius: DesignTokens.Radius.sm)
                }
            } else if recent.isEmpty {
                Text("No history yet. Run an analysis to see results here.")
                    .font(DesignTokens.Typography.caption)
                    .foregroundStyle(DesignTokens.Color.muted)
            } else {
                ForEach(recent) { item in
                    Button {
                        loadHistoryPreview(path: item.path)
                        setChatContext(selection: "history", overridePath: item.path)
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                                Text(item.name)
                                    .maText(.body)
                                Text(item.modified, style: .relative)
                                    .maText(.caption)
                                    .foregroundStyle(DesignTokens.Color.muted)
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundStyle(DesignTokens.Color.muted)
                        }
                        .padding(.vertical, DesignTokens.Spacing.xs)
                    }
                    .buttonStyle(.plain)
                    .contentShape(Rectangle())
                    .overlay(alignment: .trailing) {
                        Button {
                            setChatContext(selection: "history", overridePath: item.path)
                            store.dispatch(.setPrompt("Explain the history item \(item.name) and what to do next."))
                            showChatOverlay = true
                        } label: {
                            Image(systemName: "questionmark.circle")
                                .font(.system(size: 12, weight: .medium))
                        }
                        .maButton(.ghost)
                        .padding(.trailing, DesignTokens.Spacing.xs)
                    }
                }
            }
        }
        .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg, shadow: DesignTokens.Shadow.subtle)
    }

    private var latestResultCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text("Latest result")
                    .font(DesignTokens.Typography.headline)
                Spacer()
                Button("Open Analyze") {
                    store.dispatch(.setRoute(.analyze(store.state.route.runPane)))
                }
                .maButton(.ghost)
            }
            if viewModel.summaryMetrics.isEmpty && viewModel.sidecarPath == nil {
                Text("Run analysis to see HCI, axes, and sidecar previews.")
                    .font(DesignTokens.Typography.caption)
                    .foregroundStyle(DesignTokens.Color.muted)
            } else {
                HStack(spacing: DesignTokens.Spacing.sm) {
                    ForEach(viewModel.summaryMetrics) { metric in
                        VStack(alignment: .leading) {
                            Text(metric.label).maText(.caption).foregroundStyle(DesignTokens.Color.muted)
                            Text(metric.value).maText(.body)
                        }
                        .maMetric()
                    }
                    if let path = viewModel.sidecarPath {
                        Button("Reveal sidecar") { revealSidecar(path: path) }
                            .maButton(.ghost)
                    }
                    Spacer()
                }
            }
        }
        .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg, shadow: DesignTokens.Shadow.subtle)
    }

    private var analyzeView: some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
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
                    store.dispatch(.setRoute(store.state.route.updatingTab(.library)))
                }
            )
            .frame(maxWidth: .infinity, alignment: .topLeading)

            if store.state.showAdvanced {
                InspectorPanel(
                    mode: .analyze,
                    workingDirectory: viewModel.workingDirectory,
                    envText: viewModel.envText,
                    sidecarPath: viewModel.sidecarPath,
                    lastStatus: viewModel.status,
                    echoStatuses: Array(store.state.echoStatuses.values),
                    onRevealSidecar: {
                        if let path = viewModel.sidecarPath { revealSidecar(path: path) }
                    },
                    onCopySidecar: {
                        if let path = viewModel.sidecarPath {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(path, forType: .string)
                        }
                    }
                )
                .frame(width: 320)
            }
        }
        .padding(.trailing, DesignTokens.Spacing.md)
    }

    private var resultsDashboard: some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
            VStack(spacing: DesignTokens.Spacing.md) {
                if let last = viewModel.lastRunTime {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                            Text("Last run")
                                .maText(.caption)
                                .foregroundStyle(DesignTokens.Color.muted)
                            let rel = RelativeDateTimeFormatter().localizedString(for: last, relativeTo: Date())
                            Text(rel)
                                .maText(.body)
                        }
                        if let path = viewModel.sidecarPath {
                            Text(URL(fileURLWithPath: path).lastPathComponent)
                                .maText(.caption)
                                .foregroundStyle(DesignTokens.Color.muted)
                        }
                        Spacer()
                    }
                    .cardSurface(padding: DesignTokens.Spacing.sm, cornerRadius: DesignTokens.Radius.md, shadow: DesignTokens.Shadow.subtle)
                }
                if viewModel.isRunning && viewModel.summaryMetrics.isEmpty {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        ForEach(0..<3) { _ in
                            SkeletonView(height: 48, cornerRadius: DesignTokens.Radius.sm)
                        }
                    }
                    .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg)
                } else if !viewModel.summaryMetrics.isEmpty {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        ForEach(viewModel.summaryMetrics) { metric in
                            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                                Text(metric.label).maText(.caption).foregroundStyle(DesignTokens.Color.muted)
                                Text(metric.value).maText(.body)
                            }
                            .maMetric()
                            .maHoverLift()
                        }
                        Spacer()
                    }
                    .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg)
                }
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
                .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg)
            }
            .frame(maxWidth: .infinity, alignment: .topLeading)

            if store.state.showAdvanced {
                InspectorPanel(
                    mode: .results,
                    workingDirectory: viewModel.workingDirectory,
                    envText: viewModel.envText,
                    sidecarPath: viewModel.sidecarPath,
                    lastStatus: viewModel.status,
                    echoStatuses: Array(store.state.echoStatuses.values),
                    onRevealSidecar: {
                        if let path = viewModel.sidecarPath { revealSidecar(path: path) }
                    },
                    onCopySidecar: {
                        if let path = viewModel.sidecarPath {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(path, forType: .string)
                        }
                    }
                )
                .frame(width: 320)
            }
        }
        .padding(.trailing, DesignTokens.Spacing.md)
    }

    private var echoView: some View {
        HistoricalEchoPanel(store: store,
                            isLoading: store.state.echoStatuses.isEmpty && viewModel.isRunning,
                            isEnabled: echoEnabled)
            .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg)
            .padding(.trailing, DesignTokens.Spacing.md)
    }

    private var guidePanel: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
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
        }
        .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg)
        .padding(.trailing, DesignTokens.Spacing.md)
    }

    private var settingsPanel: some View {
        SettingsView(useDarkTheme: Binding(get: { store.state.useDarkTheme },
                                           set: { value in
                                               store.dispatch(.setFollowSystemTheme(false))
                                               store.dispatch(.setTheme(value))
                                               applyTheme(value)
                                           }),
                     statusText: store.commandVM.status,
                     dataPath: applicationSupportPath())
            .cardSurface(padding: DesignTokens.Spacing.md, cornerRadius: DesignTokens.Radius.lg)
            .padding(.trailing, DesignTokens.Spacing.md)
    }

    private func routeSubtitle(for tab: AppTab) -> String {
        switch tab {
        case .library: return "Import, queue, and browse recent runs."
        case .analyze: return "Configure and run analysis with zero lag."
        case .results: return "Review HCI, axes, logs, and sidecars."
        case .echo: return "Historical Echo submissions and cache."
        case .guide: return "Chat-based guide with contextual snippets."
        case .settings: return "Appearance, paths, and diagnostics."
        }
    }

    // MARK: - Formatting helpers

    private func prettyJSON(_ dict: [String: AnyHashable]) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: [.prettyPrinted]),
              let str = String(data: data, encoding: .utf8) else {
            return dict.isEmpty ? "(no JSON parsed)" : dict.description
        }
        return str
    }

    private func paletteEntries() -> [CommandPalette.Entry] {
        var entries: [CommandPalette.Entry] = [
            CommandPalette.Entry(title: "Import audio…", subtitle: "Pick audio and prep Analyze", action: {
                if let url = services.filePicker.pickFile() {
                    viewModel.insertAudioPath(url.path)
                    trackVM?.ingestDropped(urls: [url])
                    store.dispatch(.setRoute(.analyze(store.state.route.runPane)))
                }
            }),
            CommandPalette.Entry(title: "Run analysis", subtitle: "Run current command or queue", action: {
                Task { @MainActor in viewModel.runQueueOrSingle() }
            }),
            CommandPalette.Entry(title: "Open Results", subtitle: "Latest run outputs", action: {
                store.dispatch(.setRoute(.results(store.state.route.runPane)))
            }),
            CommandPalette.Entry(title: "Open Historical Echo", subtitle: "Broker status and cache", action: {
                store.dispatch(.setRoute(.echo))
            }),
            CommandPalette.Entry(title: "Open Guide", subtitle: "Chat with context", action: {
                showChatOverlay = true
            })
        ]
        if let path = viewModel.sidecarPath {
            entries.append(CommandPalette.Entry(title: "Copy sidecar path", subtitle: path, action: {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(path, forType: .string)
            }))
        }
        return entries
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

    private var contextRibbon: some View {
        let hci = viewModel.summaryMetrics.first(where: { $0.label.lowercased().contains("hci") })?.value
        let axes = viewModel.summaryMetrics.filter { !$0.label.lowercased().contains("hci") }.map { ($0.label, $0.value) }
        let nextMove: String
        if viewModel.isRunning {
            nextMove = "Running…"
        } else if viewModel.sidecarPath != nil {
            nextMove = "Review sidecar and Echo"
        } else if !viewModel.commandText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            nextMove = "Run analysis"
        } else {
            nextMove = "Import audio"
        }
        let steps: [ContextRibbon.Step] = [
            .init(title: "Import", status: viewModel.commandText.isEmpty ? "idle" : "done", action: { setChatContext(selection: "none", overridePath: nil) }),
            .init(title: "Run", status: viewModel.isRunning ? "running" : (viewModel.sidecarPath != nil ? "done" : "ready"), action: { store.dispatch(.setRoute(.analyze(store.state.route.runPane))) }),
            .init(title: "Review", status: viewModel.sidecarPath != nil ? "ready" : "idle", action: { store.dispatch(.setRoute(.results(store.state.route.runPane))) }),
            .init(title: "Echo", status: store.state.echoStatuses.isEmpty ? "idle" : "ready", action: { store.dispatch(.setRoute(.echo)) })
        ]

        return ContextRibbon(
            hciValue: hci,
            axes: axes,
            nextMove: nextMove,
            contextLabel: store.state.chatBadgeTitle,
            contextSubtitle: store.state.chatBadgeSubtitle,
            steps: steps
        )
        .frame(maxHeight: 74)
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
            Button(action: { showPalette = true }) { EmptyView() }
                .keyboardShortcut("k", modifiers: [.command])
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}

struct HistoricalEchoPanel: View {
    @ObservedObject var store: AppStore
    var isLoading: Bool = false
    var isEnabled: Bool = true
    @State private var retryingFetch: Set<String> = []

    var body: some View {
        let statuses = Array(store.state.echoStatuses.values).sorted { $0.trackId < $1.trackId }
        return VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text("Historical Echo")
                    .maText(.headline)
                Spacer()
                Text("\(statuses.count) tracked")
                    .maText(.caption)
                    .foregroundStyle(DesignTokens.Color.muted)
            }
            let cachePath = cacheBasePath()
            Text("Cache base: \(cachePath)")
                .maText(.caption)
                .foregroundStyle(isSandboxPath(cachePath) ? MAStyle.ColorToken.warning : DesignTokens.Color.muted)
            if !isEnabled {
                Text("Historical Echo disabled (set MA_ECHO_BROKER_ENABLE=1)")
                    .maText(.caption)
                    .foregroundStyle(DesignTokens.Color.muted)
            } else if isLoading {
                VStack(spacing: DesignTokens.Spacing.sm) {
                    ForEach(0..<3) { _ in
                        SkeletonView(height: 52, cornerRadius: DesignTokens.Radius.sm)
                    }
                }
            } else if statuses.isEmpty {
                Text("No broker submissions yet.")
                    .maText(.caption)
                    .foregroundStyle(DesignTokens.Color.muted)
            } else {
                ForEach(statuses, id: \.trackId) { status in
                    echoStatusRow(status)
                        .padding(DesignTokens.Spacing.xs)
                        .background(DesignTokens.Color.surface.opacity(0.35))
                        .cornerRadius(DesignTokens.Radius.sm)
                }
            }
        }
    }

    private func echoStatusRow(_ status: EchoStatus) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            HStack {
                Text(status.trackId).maText(.body)
                Spacer()
                Text(status.status.uppercased())
                    .maText(.caption)
                    .foregroundStyle(color(for: status.status))
            }
            if let job = status.jobId {
                Text("job_id: \(job)").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
            }
            if let cfg = status.configHash, let src = status.sourceHash {
                let cfgShort = String(cfg.prefix(8))
                let srcShort = String(src.prefix(8))
                Text("config: \(cfgShort)…  source: \(srcShort)…").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
            }
            if let n = status.neighborCount {
                Text("neighbors: \(n)").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
            }
            if let dec = status.decadeSummary {
                Text("decades: \(dec)").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
            }
            if let preview = status.neighborsPreview, !preview.isEmpty {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text("neighbors:").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
                    ForEach(preview, id: \.self) { line in
                        Text("• \(line)").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
                    }
                }
            }
            if let art = status.artifact {
                Text("artifact: \(art)").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
            }
            if let cached = status.cachedPath {
                HStack(spacing: DesignTokens.Spacing.xs) {
                    Text("cached: \(cached)").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
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
            HStack(spacing: DesignTokens.Spacing.xs) {
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
                    Text("retry if stale or failed").maText(.caption).foregroundStyle(DesignTokens.Color.muted)
                }
            }
            if let err = status.error {
                Text("error: \(err)").maText(.caption).foregroundStyle(Color.red)
            }
        }
    }

    private func color(for status: String) -> Color {
        switch status.lowercased() {
        case "done": return Color.green
        case "no_features": return Color.yellow
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

    private func startRetryFetch(trackId: String) {
        if retryingFetch.contains(trackId) { return }
        retryingFetch.insert(trackId)
        Task {
            defer { Task { @MainActor in retryingFetch.remove(trackId) } }
            await store.retryEchoFetch(trackId: trackId)
        }
    }

    private func canRetrySubmit(_ trackId: String) -> Bool {
        return store.state.queueJobs.contains { $0.displayName == trackId && $0.sidecarPath != nil }
    }

    private func cacheBasePath() -> String {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?
            .appendingPathComponent("MusicAdvisorMacApp/echo_cache", isDirectory: true)
        return dir?.path ?? "(unknown)"
    }

    private func isSandboxPath(_ path: String) -> Bool {
        return path.contains("/hosts/macos_app/build/home")
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
        historyReloadTask = Task(priority: .utility) {
            await MainActor.run { historyLoading = true }
            await reloadHistoryAsync()
            await MainActor.run { historyLoading = false }
        }
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
            await MainActor.run { historyLoading = true }
            try? await Task.sleep(nanoseconds: 350_000_000)
            await reloadHistoryAsync()
            await MainActor.run { historyLoading = false }
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
        case .library: return "Library"
        case .analyze: return "Analyze"
        case .results: return "Results"
        case .echo: return "Historical Echo"
        case .guide: return "Guide"
        case .settings: return "Settings"
        }
    }
}
