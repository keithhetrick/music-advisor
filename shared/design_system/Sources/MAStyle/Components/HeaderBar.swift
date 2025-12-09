import SwiftUI

// MARK: - HeaderBar
/// Simple header bar with title/subtitle and trailing actions.
public struct HeaderBar<Trailing: View>: View {
    let title: String
    let subtitle: String?
    let trailing: Trailing

    public init(title: String, subtitle: String? = nil, @ViewBuilder trailing: () -> Trailing) {
        self.title = title
        self.subtitle = subtitle
        self.trailing = trailing()
    }

    public var body: some View {
        HStack(alignment: .center, spacing: MAStyle.Spacing.sm) {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text(title)
                    .maText(.headline)
                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
            }
            Spacer()
            trailing
        }
    }
}
