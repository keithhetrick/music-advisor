import Foundation

/// Global wrapper that could coordinate processing + recommendation + host state.
actor HostCoordinator {
    private let processing: ProcessingService
    private let recommendation: RecommendationService
    private var snapshotValue: HostSnapshot = .idle

    init(processing: ProcessingService = ProcessingService(),
         recommendation: RecommendationService = RecommendationService()) {
        self.processing = processing
        self.recommendation = recommendation
    }

    func snapshot() async -> HostSnapshot {
        let p = await processing.snapshot()
        let r = await recommendation.snapshot()
        snapshotValue = HostSnapshot(processing: p, recommendation: r, status: "ok", lastUpdated: Date())
        return snapshotValue
    }

    func updateStatus(_ status: String) {
        snapshotValue.status = status
        snapshotValue.lastUpdated = Date()
    }

    func updateProcessing(status: String? = nil, progress: Double? = nil, message: String? = nil) async {
        await processing.update(status: status, progress: progress, message: message)
    }
}
