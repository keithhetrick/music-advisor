import Foundation

/// Thin actor wrapper for processing/queue operations.
/// Today it just holds a snapshot; wire run/queue operations here as they evolve.
actor ProcessingService {
    private var snapshotValue: ProcessingSnapshot = .idle

    func snapshot() -> ProcessingSnapshot {
        snapshotValue
    }

    func update(status: String? = nil, progress: Double? = nil, message: String? = nil) {
        if let status { snapshotValue.status = status }
        if let progress { snapshotValue.progress = progress }
        if let message { snapshotValue.lastMessage = message }
        snapshotValue.lastUpdated = Date()
    }
}
