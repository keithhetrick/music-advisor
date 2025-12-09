import Foundation

struct HistoryPreview: Equatable, Codable {
    var sidecar: String
    var rich: String?
    var richFound: Bool = false
    var richPath: String?
}

