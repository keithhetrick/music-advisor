import SwiftUI
import AppKit
import MAStyle

struct ContentView: View {
    @StateObject private var viewModel = CommandViewModel()
    @State private var selectedPane: ResultPane = .json
    private enum Tab: String, CaseIterable { case run = "Pipeline", history = "History" }
    @State private var selectedTab: Tab = .run
    @AppStorage("useDarkTheme") private var useDarkTheme: Bool = true
    @State private var promptText: String = ""
    @State private var messages: [String] = ["Welcome to Music Advisor!"]
    @State private var showAdvanced: Bool = false
    @State private var historyItems: [SidecarItem] = []
    @State private var historyReloadWork: DispatchWorkItem?
    @State private var historyPreviews: [String: HistoryPreview] = [:]
    @State private var previewCache: [String: HistoryPreview] = [:]
    private let mockTrackTitle = "Track Title — Artist"
    private let quickActions: [(title: String, symbol: String)] = [
        ("Warnings", "exclamationmark.triangle.fill"),
        ("Quick Actions", "bolt.fill"),
        ("Norms", "chart.bar.doc.horizontal.fill")
    ]
    private let sections = ["HCI", "Axes", "Historical Echo", "Optimization / Plan"]
    @State private var trackVM: TrackListViewModel?

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    MAStyle.ColorToken.background,
                    MAStyle.ColorToken.panel.opacity(0.85)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
                .ignoresSafeArea()
            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                HeaderView()
                    .maSheen(isActive: viewModel.isRunning, duration: 4.5)
                Divider()
                SettingsView(useDarkTheme: $useDarkTheme, statusText: viewModel.status)
                Divider()
                Picker("Tab", selection: $selectedTab) {
                    ForEach(Tab.allCases, id: \.self) { tab in
                        Text(tab.rawValue).tag(tab)
                    }
                }
                .pickerStyle(.segmented)
                ScrollView {
                    if selectedTab == .run {
                        mainSplit
                            .frame(maxWidth: .infinity, alignment: .leading)
                    } else {
                        historyPane
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            .padding(MAStyle.Spacing.lg)
            .frame(minWidth: 640, minHeight: 420)
        }
        .preferredColorScheme(useDarkTheme ? .dark : .light)
        .onAppear {
            applyTheme(useDarkTheme)
            if trackVM == nil {
                trackVM = makeTrackViewModel()
            }
            reloadHistory()
        }
        .onChange(of: useDarkTheme) { isDark in
            applyTheme(isDark)
        }
        .onReceive(viewModel.queueVM.objectWillChange) { _ in
            scheduleHistoryReload()
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
                Toggle("", isOn: $useDarkTheme)
                    .toggleStyle(.switch)
                    .labelsHidden()
                    .onChange(of: useDarkTheme) { newValue in
                        if newValue {
                            MAStyle.useDarkTheme()
                        } else {
                            MAStyle.useLightTheme()
                        }
                    }
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
            TrackHeaderView(title: mockTrackTitle, badgeText: "Norms Badge")
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
            QuickActionsView(actions: quickActions)
            SectionsView(sections: sections)
            if let trackVM {
                TrackListView(viewModel: trackVM)
            }
                CommandInputsView(
                    profiles: viewModel.profiles,
                    selectedProfile: $viewModel.selectedProfile,
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
                    showAdvanced: $showAdvanced,
                    commandText: $viewModel.commandText,
                    workingDirectory: $viewModel.workingDirectory,
                    envText: $viewModel.envText,
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
                    selectedPane: $selectedPane,
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
        HistoryView(
            items: historyItems,
            onRefresh: reloadHistory,
            onReveal: revealSidecar(path:),
            onPreview: { path in
                loadHistoryPreview(path: path)
            },
            previews: historyPreviews
        )
    }

    private var leftColumn: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            ConsoleView(messages: messages)
            PromptView(text: $promptText, onSend: sendMessage)
        }
    }

    private var trackHeader: some View {
        HStack {
            Text(mockTrackTitle)
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
                ForEach(quickActions, id: \.title) { action in
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
            ForEach(sections, id: \.self) { section in
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
            Picker("", selection: $selectedPane) {
                Text("JSON").tag(ResultPane.json)
                Text("stdout").tag(ResultPane.stdout)
                Text("stderr").tag(ResultPane.stderr)
            }
            .pickerStyle(.segmented)
            .onChange(of: viewModel.parsedJSON, perform: { _ in
                if selectedPane == .json && viewModel.parsedJSON.isEmpty {
                    selectedPane = .stdout
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

            resultBlock(title: selectedPane.title,
                        text: paneText(selectedPane),
                        color: selectedPane.color)

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
        let trimmed = promptText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        messages.append(trimmed)
        promptText = ""
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
            return viewModel.stdout
        case .stderr:
            return viewModel.stderr
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}

enum ResultPane: Hashable {
    case json, stdout, stderr

    var title: String {
        switch self {
        case .json: return "parsed JSON"
        case .stdout: return "stdout"
        case .stderr: return "stderr"
        }
    }

    var color: Color {
        switch self {
        case .json: return .blue
        case .stdout: return .green
        case .stderr: return .red
        }
    }
}

// MARK: - Pickers
extension ContentView {
    private func pickFile() -> URL? {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        let response = panel.runModal()
        return response == .OK ? panel.urls.first : nil
    }

    private func pickDirectory() -> URL? {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        let response = panel.runModal()
        return response == .OK ? panel.urls.first : nil
    }

    private func revealSidecar(path: String) {
        let url = URL(fileURLWithPath: path)
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
        let fm = FileManager.default
        let supportDir = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let sidecarDir = supportDir.appendingPathComponent("MusicAdvisorMacApp/sidecars", isDirectory: true)
        guard let urls = try? fm.contentsOfDirectory(at: sidecarDir, includingPropertiesForKeys: [.contentModificationDateKey], options: [.skipsHiddenFiles]) else {
            historyItems = []
            return
        }
        let items: [SidecarItem] = urls.compactMap { url in
            let attrs = try? url.resourceValues(forKeys: [.contentModificationDateKey])
            let mod = attrs?.contentModificationDate ?? Date.distantPast
            return SidecarItem(path: url.path, name: url.lastPathComponent, modified: mod)
        }
        historyItems = items.sorted { $0.modified > $1.modified }
    }

    private func scheduleHistoryReload() {
        historyReloadWork?.cancel()
        let work = DispatchWorkItem { reloadHistory() }
        historyReloadWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35, execute: work)
    }

    private func loadHistoryPreview(path: String) {
        if let cached = previewCache[path] {
            historyPreviews[path] = cached
            return
        }
        Task.detached {
            let fm = FileManager.default
            let sidecarText: String
            if let data = fm.contents(atPath: path),
               let txt = String(data: data, encoding: .utf8) {
                sidecarText = txt
            } else {
                sidecarText = "(unreadable)"
            }
            var richText: String?
            var richFound = false
            var richPathUsed: String?
            // Try sibling rich file first.
            let richPath = path.replacingOccurrences(of: ".json", with: ".client.rich.txt")
            if fm.fileExists(atPath: richPath),
               let data = fm.contents(atPath: richPath),
               let txt = String(data: data, encoding: .utf8) {
                richText = txt
                richFound = true
                richPathUsed = richPath
            } else {
                // Fallback: search the repo features_output tree for a matching rich file by basename.
                let baseName = URL(fileURLWithPath: path).deletingPathExtension().lastPathComponent
                var candidates: [String] = [baseName]
                if let lastUnderscore = baseName.lastIndex(of: "_") {
                    let truncated = String(baseName[..<lastUnderscore])
                    candidates.append(truncated)
                }
                let repoRoot = URL(fileURLWithPath: "/Users/keithhetrick/music-advisor")
                let featuresRoot = repoRoot.appendingPathComponent("data/features_output")
                if let enumerator = fm.enumerator(at: featuresRoot, includingPropertiesForKeys: nil) {
                    for case let url as URL in enumerator {
                        for candidate in candidates {
                            if url.lastPathComponent == "\(candidate).client.rich.txt",
                               let data = try? Data(contentsOf: url),
                               let txt = String(data: data, encoding: .utf8) {
                                richText = txt
                                richFound = true
                                richPathUsed = url.path
                                break
                            }
                        }
                        if richFound { break }
                    }
                }
            }
            let preview = HistoryPreview(sidecar: sidecarText, rich: richText, richFound: richFound, richPath: richPathUsed)
            await MainActor.run {
                var cacheCopy = previewCache
                cacheCopy[path] = preview
                previewCache = cacheCopy
                var historyCopy = historyPreviews
                historyCopy[path] = preview
                historyPreviews = historyCopy
            }
        }
    }
}

struct HistoryPreview: Hashable {
    let sidecar: String
    let rich: String?
    let richFound: Bool
    let richPath: String?
}
