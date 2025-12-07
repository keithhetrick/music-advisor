import Foundation

struct Job: Identifiable, Hashable {
    enum Status: String, Hashable {
        case pending, running, done, failed
    }

    let id = UUID()
    let fileURL: URL
    let displayName: String
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
        case .done, .failed: return 1.0
        }
    }
}
