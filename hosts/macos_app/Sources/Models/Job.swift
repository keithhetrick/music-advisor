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
}
