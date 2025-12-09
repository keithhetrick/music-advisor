import SwiftUI

// MARK: - CardHeader
/// Reusable card header with optional subtitle, badge, and trailing action.
public struct CardHeader: View {
    let title: String
    let subtitle: String?
    let badge: String?
    let actionTitle: String?
    let action: (() -> Void)?

    public init(title: String,
                subtitle: String? = nil,
                badge: String? = nil,
                actionTitle: String? = nil,
                action: (() -> Void)? = nil) {
        self.title = title
        self.subtitle = subtitle
        self.badge = badge
        self.actionTitle = actionTitle
        self.action = action
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
            if let badge, !badge.isEmpty {
                Text(badge)
                    .maChip(style: .solid, color: MAStyle.ColorToken.info)
            }
            Spacer()
            if let actionTitle, let action {
                Button(actionTitle) { action() }
                    .maButton(.ghost)
            }
        }
    }
}
