import SwiftUI

// MARK: - Rail toggle overlay helper
/// A reusable overlay wrapper for the compact RailToggle. It handles positioning
/// relative to a rail edge, hover tuck, and padding so host apps can drop it in
/// with one line.
public struct RailToggleOverlay: View {
    let isShown: Bool
    let railWidth: CGFloat
    let topPadding: CGFloat
    let hiddenEdgePadding: CGFloat
    let onToggle: () -> Void

    public init(
        isShown: Bool,
        railWidth: CGFloat = 72,
        topPadding: CGFloat = MAStyle.Spacing.md,
        hiddenEdgePadding: CGFloat = MAStyle.Spacing.md,
        onToggle: @escaping () -> Void
    ) {
        self.isShown = isShown
        self.railWidth = railWidth
        self.topPadding = topPadding
        self.hiddenEdgePadding = hiddenEdgePadding
        self.onToggle = onToggle
    }

    public var body: some View {
        RailToggle(
            state: isShown ? .shown : .hidden,
            compact: true,
            slideFromLeft: !isShown,
            toggle: onToggle
        )
        .padding(.top, topPadding)
        .padding(.leading, leadingInset)
        .zIndex(5)
        .animation(.spring(response: 0.42, dampingFraction: 0.85), value: isShown)
    }

    // When rail is visible, hug the rail/content border; when hidden, float just off the edge.
    private var leadingInset: CGFloat {
        if isShown {
            return railWidth - (MAStyle.Spacing.xs * 0.5)
        } else {
            return hiddenEdgePadding
        }
    }
}
