import Foundation

public struct TaskConductorConfig: Sendable {
    public var defaultWorkingDirectory: String?
    public var defaultEnvironment: [String: String]
    public var defaultTimeoutSeconds: TimeInterval?
    public var globalLogURL: URL?
    public var maxConcurrentTasks: Int
    public var maxQueueDepth: Int?
    public var retryCount: Int
    public var retryDelaySeconds: TimeInterval
    public var retryJitterSeconds: TimeInterval
    public var logRotationBytes: Int?
    public var logLineHandler: (@Sendable (String) -> Void)?
    public var extraLogHandler: (@Sendable (TaskEvent) -> Void)?

    public init(
        defaultWorkingDirectory: String? = nil,
        defaultEnvironment: [String: String] = [:],
        defaultTimeoutSeconds: TimeInterval? = nil,
        globalLogURL: URL? = nil,
        maxConcurrentTasks: Int = 2,
        maxQueueDepth: Int? = nil,
        retryCount: Int = 0,
        retryDelaySeconds: TimeInterval = 0,
        retryJitterSeconds: TimeInterval = 0,
        logRotationBytes: Int? = nil,
        logLineHandler: (@Sendable (String) -> Void)? = nil,
        extraLogHandler: (@Sendable (TaskEvent) -> Void)? = nil
    ) {
        self.defaultWorkingDirectory = defaultWorkingDirectory
        self.defaultEnvironment = defaultEnvironment
        self.defaultTimeoutSeconds = defaultTimeoutSeconds
        self.globalLogURL = globalLogURL
        self.maxConcurrentTasks = maxConcurrentTasks
        self.maxQueueDepth = maxQueueDepth
        self.retryCount = retryCount
        self.retryDelaySeconds = retryDelaySeconds
        self.retryJitterSeconds = retryJitterSeconds
        self.logRotationBytes = logRotationBytes
        self.logLineHandler = logLineHandler
        self.extraLogHandler = extraLogHandler
    }
}
