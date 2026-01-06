import Foundation

/// Top-level navigation for the host app.
enum AppRoute: Equatable {
    case library
    case analyze(ResultPane)
    case results(ResultPane)
    case echo
    case guide
    case settings

    var tab: AppTab {
        switch self {
        case .library: return .library
        case .analyze: return .analyze
        case .results: return .results
        case .echo: return .echo
        case .guide: return .guide
        case .settings: return .settings
        }
    }

    /// Shared pane selection used by Analyze and Results.
    var runPane: ResultPane {
        switch self {
        case .analyze(let pane): return pane
        case .results(let pane): return pane
        default: return .json
        }
    }

    func updatingTab(_ tab: AppTab) -> AppRoute {
        switch tab {
        case .library: return .library
        case .analyze: return .analyze(self.runPane)
        case .results: return .results(self.runPane)
        case .echo: return .echo
        case .guide: return .guide
        case .settings: return .settings
        }
    }

    func updatingRunPane(_ pane: ResultPane) -> AppRoute {
        switch self {
        case .analyze: return .analyze(pane)
        case .results: return .results(pane)
        default: return self
        }
    }
}
