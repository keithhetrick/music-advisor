import Foundation

public struct TaskDescriptor: Sendable {
    public var id: UUID
    public var command: [String]
    public var workingDirectory: String?
    public var environment: [String: String]
    /// Optional timeout in seconds. If nil, no timeout is applied.
    public var timeoutSeconds: TimeInterval?
    /// Optional per-task log file. If nil, only the shared logger is used.
    public var perTaskLogURL: URL?

    public init(
        id: UUID = UUID(),
        command: [String],
        workingDirectory: String? = nil,
        environment: [String: String] = [:],
        timeoutSeconds: TimeInterval? = nil,
        perTaskLogURL: URL? = nil
    ) {
        self.id = id
        self.command = command
        self.workingDirectory = workingDirectory
        self.environment = environment
        self.timeoutSeconds = timeoutSeconds
        self.perTaskLogURL = perTaskLogURL
    }
}
