import Foundation
import Combine

/// Tracks whether a scrollable view is off the bottom and provides a publisher to drive a jump button.
public final class ScrollToBottomController: ObservableObject {
    @Published public private(set) var showJump: Bool = false
    private var isAtBottom: Bool = true

    public init() {}

    /// Call when the view auto-scrolled to bottom (e.g., on new content).
    public func didScrollToBottom() {
        isAtBottom = true
        showJump = false
    }

    /// Call on user drag/scroll to indicate they left the bottom.
    public func didScrollAway() {
        if isAtBottom {
            isAtBottom = false
            showJump = true
        }
    }

    /// Call when a jump-to-bottom is triggered.
    public func jump() {
        isAtBottom = true
        showJump = false
    }
}
