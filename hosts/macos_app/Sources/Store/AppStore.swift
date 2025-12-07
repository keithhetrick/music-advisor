import Foundation
import SwiftUI

enum AppTab: String, CaseIterable {
    case run = "Pipeline"
    case history = "History"
    case style = "MAStyle"
}

enum AppAction {
    case setTheme(Bool)
    case setTab(AppTab)
    case setPane(ResultPane)
    case setPrompt(String)
    case appendMessage(String)
    case setMessages([String])
    case setShowAdvanced(Bool)
    case setHistoryItems([SidecarItem])
    case setHistoryPreview(path: String, preview: HistoryPreview)
    case setPreviewCache(path: String, preview: HistoryPreview)
    case clearHistory
    case setHostSnapshot(HostSnapshot)
}

struct AppState {
    var useDarkTheme: Bool = true
    var selectedTab: AppTab = .run
    var selectedPane: ResultPane = .json
    var promptText: String = ""
    var messages: [String] = ["Welcome to Music Advisor!"]
    var showAdvanced: Bool = false
    var historyItems: [SidecarItem] = []
    var historyPreviews: [String: HistoryPreview] = [:]
    var previewCache: [String: (HistoryPreview, Date?)] = [:]
    var hostSnapshot: HostSnapshot = .idle
    // UI literals made dynamic for future tweaks.
    var mockTrackTitle: String = "Track Title — Artist"
    var quickActions: [(title: String, symbol: String)] = [
        ("Warnings", "exclamationmark.triangle.fill"),
        ("Quick Actions", "bolt.fill"),
        ("Norms", "chart.bar.doc.horizontal.fill")
    ]
    var sections: [String] = ["HCI", "Axes", "Historical Echo", "Optimization / Plan"]
}

@MainActor
final class AppStore: ObservableObject {
    @Published var state = AppState()

    // Adapters to keep existing bindings working while we refactor views to scoped state later.
    let commandVM: CommandViewModel
    let trackVM: TrackListViewModel?
    private let hostCoordinator: HostCoordinator
    private var hostMonitorTask: Task<Void, Never>?

    func dispatch(_ action: AppAction) {
        switch action {
        case .setTheme(let value):
            state.useDarkTheme = value
        case .setTab(let tab):
            state.selectedTab = tab
        case .setPane(let pane):
            state.selectedPane = pane
        case .setPrompt(let text):
            state.promptText = text
        case .appendMessage(let msg):
            state.messages.append(msg)
        case .setMessages(let msgs):
            state.messages = msgs
        case .setShowAdvanced(let value):
            state.showAdvanced = value
        case .setHistoryItems(let items):
            state.historyItems = items
        case .setHistoryPreview(let path, let preview):
            state.historyPreviews[path] = preview
        case .setPreviewCache(let path, let preview):
            // Keep old mtime if present (will be overridden by caller when needed).
            let currentMtime = state.previewCache[path]?.1
            state.previewCache[path] = (preview, currentMtime)
        case .clearHistory:
            state.historyItems = []
            state.historyPreviews = [:]
            state.previewCache = [:]
        case .setHostSnapshot(let snap):
            state.hostSnapshot = snap
        }
    }

    init() {
        self.hostCoordinator = HostCoordinator()
        self.commandVM = CommandViewModel()
        self.trackVM = AppStore.makeTrackViewModel()
        self.commandVM.processingUpdater = { [weak self] status, progress, message in
            Task {
                await self?.hostCoordinator.updateProcessing(status: status, progress: progress, message: message)
            }
        }
        startHostMonitor()
    }

    deinit {
        hostMonitorTask?.cancel()
    }

    private static func trackStorePaths() -> (trackURL: URL, artistURL: URL) {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let trackURL = appDir.appendingPathComponent("tracks.json")
        let artistURL = appDir.appendingPathComponent("artists.json")
        return (trackURL, artistURL)
    }

    private static func makeTrackViewModel() -> TrackListViewModel {
        let paths = trackStorePaths()
        let trackStore = JsonTrackStore(url: paths.trackURL)
        let artistStore = JsonArtistStore(url: paths.artistURL)
        return TrackListViewModel(trackStore: trackStore, artistStore: artistStore)
    }

    private func startHostMonitor() {
        hostMonitorTask?.cancel()
        hostMonitorTask = Task.detached { [weak self] in
            while let self = self {
                let snap = await self.hostCoordinator.snapshot()
                await MainActor.run {
                    self.state.hostSnapshot = snap
                }
                try? await Task.sleep(nanoseconds: 1_500_000_000) // 1.5s to reduce UI churn
            }
        }
    }
}
