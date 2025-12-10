import Foundation

struct Job: Identifiable, Hashable {
    enum Status: String, Hashable {
        case pending, running, done, failed, canceled
    }

    let id: UUID
    let fileURL: URL
    let displayName: String
    let groupID: UUID?
    let groupName: String?
    let groupRootPath: String?
    var status: Status = .pending
    var sidecarPath: String?
    var errorMessage: String?
    // Optional precomputed command/out to avoid per-run string surgery.
    var preparedCommand: [String]?
    var preparedOutPath: String?
    // Progress in [0,1]; we update coarsely (pending=0, running=0.5, done/failed=1).
    var progress: Double {
        switch status {
        case .pending: return 0.0
        case .running: return 0.5
        case .done, .failed, .canceled: return 1.0
        }
    }

    init(id: UUID = UUID(),
         fileURL: URL,
         displayName: String,
         groupID: UUID? = nil,
         groupName: String? = nil,
         groupRootPath: String? = nil,
         status: Status = .pending,
         sidecarPath: String? = nil,
         errorMessage: String? = nil,
         preparedCommand: [String]? = nil,
         preparedOutPath: String? = nil) {
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
    }
}
