import Foundation

struct AlertState: Equatable {
    enum Level: String {
        case info, warning, error
    }
    var title: String
    var message: String
    var level: Level
}
