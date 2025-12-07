import Foundation

struct ProcessingSnapshot {
    var status: String
    var progress: Double
    var lastMessage: String
    var lastUpdated: Date

    static let idle = ProcessingSnapshot(status: "idle", progress: 0, lastMessage: "", lastUpdated: Date())
}

struct RecommendationSnapshot {
    var status: String
    var recommendations: [String]
    var lastUpdated: Date

    static let idle = RecommendationSnapshot(status: "idle", recommendations: [], lastUpdated: Date())
}

struct HostSnapshot {
    var processing: ProcessingSnapshot
    var recommendation: RecommendationSnapshot
    var status: String
    var lastUpdated: Date

    static let idle = HostSnapshot(processing: .idle, recommendation: .idle, status: "idle", lastUpdated: Date())
}
