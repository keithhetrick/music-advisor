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
    let timeoutSeconds: TimeInterval
    let rateLimitSeconds: TimeInterval

    static func defaultConfig() -> ChatProviderConfig {
        let repo = ProcessInfo.processInfo.environment["MA_REPO_ROOT"]
            ?? "/Users/keithhetrick/music-advisor"
        return ChatProviderConfig(
            pythonPath: "/usr/bin/python3",
            repoRoot: repo,
            timeoutSeconds: 5.0,
            rateLimitSeconds: 0.3
        )
    }
}

protocol ChatProvider {
    func send(prompt: String, context: ChatContext, lastSent: Date?) async -> (reply: String?, rateLimited: Bool, timedOut: Bool, warning: String?, label: String, contextPath: String?, nextSentAt: Date?)
}
