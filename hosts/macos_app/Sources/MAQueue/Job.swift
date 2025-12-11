import Foundation

public struct Job: Identifiable, Hashable {
    public enum Status: String, Hashable {
        case pending, running, done, failed, canceled
    }

    public let id: UUID
    public let fileURL: URL
    public let displayName: String
    public let groupID: UUID?
    public let groupName: String?
    public let groupRootPath: String?
    public var status: Status = .pending
    public var sidecarPath: String?
    public var errorMessage: String?
    // Optional precomputed command/out to avoid per-run string surgery.
    public var preparedCommand: [String]?
    public var preparedOutPath: String?
    // Basic lifecycle tracking for resilience/recovery.
    public var createdAt: Date
    public var updatedAt: Date
    public var startedAt: Date?
    public var finishedAt: Date?
    public var attempts: Int
    // Progress in [0,1]; we update coarsely (pending=0, running=0.5, done/failed=1).
    public var progress: Double {
        switch status {
        case .pending: return 0.0
        case .running: return 0.5
        case .done, .failed, .canceled: return 1.0
        }
    }

    public init(id: UUID = UUID(),
                fileURL: URL,
                displayName: String,
                groupID: UUID? = nil,
                groupName: String? = nil,
                groupRootPath: String? = nil,
                status: Status = .pending,
                sidecarPath: String? = nil,
                errorMessage: String? = nil,
                preparedCommand: [String]? = nil,
                preparedOutPath: String? = nil,
                createdAt: Date = Date(),
                updatedAt: Date = Date(),
                startedAt: Date? = nil,
                finishedAt: Date? = nil,
                attempts: Int = 0) {
        self.id = id
        self.fileURL = fileURL
        self.displayName = displayName
        self.groupID = groupID
        self.groupName = groupName
        self.groupRootPath = groupRootPath
        self.status = status
        self.sidecarPath = sidecarPath
        self.errorMessage = errorMessage
        self.preparedCommand = preparedCommand
        self.preparedOutPath = preparedOutPath
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.startedAt = startedAt
        self.finishedAt = finishedAt
        self.attempts = attempts
    }
}
