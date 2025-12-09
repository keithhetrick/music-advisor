import Foundation

enum AlertHelper {
    static func toast(_ title: String, message: String, level: AlertState.Level = .info) -> AlertState {
        AlertState(title: title, message: message, level: level, presentAsToast: true)
    }

    static func banner(_ title: String, message: String, level: AlertState.Level = .info) -> AlertState {
        AlertState(title: title, message: message, level: level, presentAsToast: false)
    }
}

