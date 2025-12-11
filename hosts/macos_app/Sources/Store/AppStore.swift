import Foundation
import SwiftUI
import AppKit

enum AppTab: String, CaseIterable {
    case run = "Pipeline"
    case history = "History"
    case style = "MAStyle"
}

enum AppAction {
    case setAlert(AlertState?)
    case setRoute(AppRoute)
    case setTheme(Bool)
    case setFollowSystemTheme(Bool)
    case setPrompt(String)
    case appendMessage(String)
    case setMessages([String])
    case setShowAdvanced(Bool)
    case setHistoryItems([SidecarItem])
    case setHistoryPreview(path: String, preview: HistoryPreview)
    case setPreviewCache(path: String, preview: HistoryPreview)
    case clearHistory
    case setHostSnapshot(HostSnapshot)
    // Chat UI state
    case setChatBadge(title: String, subtitle: String)
    case setChatContextLabel(String)
    case setChatContextTimestamp(Date?)
    case setChatContextPath(String?)
    // Chat context
    case setChatSelection(String?)
    case setChatOverride(String?)
}

struct AppState {
    var alert: AlertState? = nil
    var route: AppRoute = .run(.json)
    var useDarkTheme: Bool = true
    var followSystemTheme: Bool = true
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
    // Chat context selection
    var chatSelection: String? = "none"
    var chatOverridePath: String? = nil
    var chatContextLabel: String = "No context"
    var chatBadgeTitle: String = "No context"
    var chatBadgeSubtitle: String = "No file"
    var chatContextLastUpdated: Date? = nil
    var chatContextPath: String? = nil
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
        reduce(&state, action: action)
    }

    init() {
        self.hostCoordinator = HostCoordinator()
        self.commandVM = CommandViewModel()
        self.trackVM = AppStore.makeTrackViewModel()
        // Seed theme from system appearance if following system.
        let systemDark = AppStore.systemPrefersDark()
        state.useDarkTheme = systemDark
        state.followSystemTheme = true
        self.commandVM.processingUpdater = { [weak self] status, progress, message in
            Task {
                await self?.hostCoordinator.updateProcessing(status: status, progress: progress, message: message)
            }
        }
        if let trackVM {
            self.commandVM.jobCompletionHandler = { job, success in
                guard success, job.status == .done else { return }
                Task { @MainActor in
                    trackVM.ingestDropped(urls: [job.fileURL])
                }
            }
            // Ensure track data is loaded even before the view appears (e.g., before scrolling).
            trackVM.load()
        }
        startHostMonitor()
    }

    deinit {
        hostMonitorTask?.cancel()
    }

    private static func trackStorePaths() -> (dbURL: URL, legacyTrackURL: URL, legacyArtistURL: URL) {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let dbURL = appDir.appendingPathComponent("MusicAdvisor.sqlite")
        let trackURL = appDir.appendingPathComponent("tracks.json")
        let artistURL = appDir.appendingPathComponent("artists.json")
        return (dbURL, trackURL, artistURL)
    }

    private static func makeTrackViewModel() -> TrackListViewModel {
        let paths = trackStorePaths()
        try? FileManager.default.createDirectory(at: paths.dbURL.deletingLastPathComponent(),
                                                 withIntermediateDirectories: true)
        let sqliteStore = try? SQLiteTrackStore(url: paths.dbURL)

        if let sqliteStore {
            migrateLegacyJSONIfNeeded(into: sqliteStore,
                                      trackURL: paths.legacyTrackURL,
                                      artistURL: paths.legacyArtistURL)
            return TrackListViewModel(trackStore: sqliteStore, artistStore: sqliteStore)
        } else {
            // Fall back to legacy JSON stores if SQLite init fails.
            let trackStore = JsonTrackStore(url: paths.legacyTrackURL)
            let artistStore = JsonArtistStore(url: paths.legacyArtistURL)
            return TrackListViewModel(trackStore: trackStore, artistStore: artistStore)
        }
    }

    private static func migrateLegacyJSONIfNeeded(into store: SQLiteTrackStore,
                                                  trackURL: URL,
                                                  artistURL: URL) {
        let jsonTrackStore = JsonTrackStore(url: trackURL)
        let jsonArtistStore = JsonArtistStore(url: artistURL)
        let hasExistingData = (try? store.listTracks().isEmpty == false) ?? false
        guard !hasExistingData else { return }
        guard FileManager.default.fileExists(atPath: trackURL.path) || FileManager.default.fileExists(atPath: artistURL.path) else {
            return
        }
        let artists = (try? jsonArtistStore.listArtists()) ?? []
        let tracks = (try? jsonTrackStore.listTracks()) ?? []
        for artist in artists {
            try? store.upsert(artist)
        }
        for track in tracks {
            try? store.upsert(track)
        }
    }

    private func startHostMonitor() {
        hostMonitorTask?.cancel()
        hostMonitorTask = Task.detached { [weak self] in
            while let self = self {
                let snap = await self.hostCoordinator.snapshot()
                await MainActor.run {
                    self.state.hostSnapshot = snap
                }
                // Back off polling when idle to reduce wakeups.
                let interval: UInt64 = snap.processing.status == "running" ? 1_500_000_000 : 3_500_000_000
                try? await Task.sleep(nanoseconds: interval)
            }
        }
    }
}

// MARK: - Reducer

private func reduce(_ state: inout AppState, action: AppAction) {
    switch action {
    case .setAlert(let alert):
        state.alert = alert
    case .setRoute(let route):
        state.route = route
    case .setTheme(let value):
        state.useDarkTheme = value
    case .setFollowSystemTheme(let value):
        state.followSystemTheme = value
    case .setPrompt(let text):
        state.promptText = text
    case .appendMessage(let msg):
        state.messages.append(msg)
        if state.messages.count > 200 {
            state.messages.removeFirst(state.messages.count - 200)
        }
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
    case .setChatBadge(let title, let subtitle):
        state.chatBadgeTitle = title
        state.chatBadgeSubtitle = subtitle
    case .setChatContextLabel(let label):
        state.chatContextLabel = label
    case .setChatContextTimestamp(let ts):
        state.chatContextLastUpdated = ts
    case .setChatContextPath(let path):
        state.chatContextPath = path
    case .setChatSelection(let sel):
        state.chatSelection = sel
    case .setChatOverride(let path):
        state.chatOverridePath = path
    }
}

extension AppStore {
    static func systemPrefersDark() -> Bool {
        let best = NSApplication.shared.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua])
        return best == .darkAqua
    }
}
