import Foundation

/// Thin actor wrapper for recommendation/state aggregation.
actor RecommendationService {
    private var snapshotValue: RecommendationSnapshot = .idle

    func snapshot() -> RecommendationSnapshot {
        snapshotValue
    }

    func update(status: String? = nil, recommendations: [String]? = nil) {
        if let status { snapshotValue.status = status }
        if let recommendations { snapshotValue.recommendations = recommendations }
        snapshotValue.lastUpdated = Date()
    }
}
