import Foundation

struct ChatContext {
    let selection: String?
    let sidecarPath: String?
    let overridePath: String?
    let historyItems: [SidecarItem]
    let previewCache: [String: (HistoryPreview, Date?)]
}

struct ChatProviderConfig {
    let pythonPath: String
    let repoRoot: String
    let timeoutNanos: UInt64
    let rateLimitSeconds: TimeInterval

    static func defaultConfig() -> ChatProviderConfig {
        let repo = ProcessInfo.processInfo.environment["MA_REPO_ROOT"]
            ?? "/Users/keithhetrick/music-advisor"
        return ChatProviderConfig(
            pythonPath: "/usr/bin/python3",
            repoRoot: repo,
            timeoutNanos: 5_000_000_000,
            rateLimitSeconds: 0.3
        )
    }
}

protocol ChatProvider {
    func send(prompt: String, context: ChatContext, lastSent: Date?) async -> (reply: String?, rateLimited: Bool, timedOut: Bool, warning: String?, label: String, nextSentAt: Date?)
}
