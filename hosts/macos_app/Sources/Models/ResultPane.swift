import Foundation
import SwiftUI

enum ResultPane: String, CaseIterable {
    case json
    case stdout
    case stderr

    var title: String {
        switch self {
        case .json: return "JSON"
        case .stdout: return "stdout"
        case .stderr: return "stderr"
        }
    }

    var color: Color {
        switch self {
        case .json: return .accentColor
        case .stdout: return .blue
        case .stderr: return .red
        }
    }
}
