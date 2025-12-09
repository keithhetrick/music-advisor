import SwiftUI

// MARK: - ToastProgressBar
/// A reusable, minimal progress indicator for toast/alert countdowns.
/// Callers drive `progress` (0...1) and can animate externally.
public struct ToastProgressBar: View {
    public let progress: CGFloat
    public let color: Color

    public init(progress: CGFloat, color: Color) {
        self.progress = progress
        self.color = color
    }

    public var body: some View {
        GeometryReader { proxy in
            Capsule()
                .fill(color.opacity(0.7))
                .frame(width: proxy.size.width * max(0, min(progress, 1)),
                       height: 3)
        }
        .frame(height: 3)
    }
}
