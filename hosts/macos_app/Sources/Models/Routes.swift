import Foundation

/// Top-level navigation for the host app.
enum AppRoute: Equatable {
    case run(ResultPane)
    case history
    case style

    var tab: AppTab {
        switch self {
        case .run: return .run
        case .history: return .history
        case .style: return .style
        }
    }

    var runPane: ResultPane {
        switch self {
        case .run(let pane): return pane
        default: return .json
        }
    }

    func updatingTab(_ tab: AppTab) -> AppRoute {
        switch tab {
        case .run:
            return .run(self.runPane)
        case .history:
            return .history
        case .style:
            return .style
        }
    }

    func updatingRunPane(_ pane: ResultPane) -> AppRoute {
        .run(pane)
    }
}
