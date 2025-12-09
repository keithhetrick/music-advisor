import SwiftUI

// MARK: - Card Header with optional badge / action
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
        HStack(alignment: .firstTextBaseline, spacing: MAStyle.Spacing.xs) {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text(title).maText(.headline)
                if let subtitle {
                    Text(subtitle)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
            }
            Spacer()
            if let badge {
                Text(badge)
                    .padding(.horizontal, MAStyle.Spacing.sm)
                    .padding(.vertical, MAStyle.Spacing.xs / 2)
                    .background(MAStyle.ColorToken.primary.opacity(0.1))
                    .foregroundColor(MAStyle.ColorToken.primary)
                    .cornerRadius(MAStyle.Radius.pill)
            }
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .maButton(.ghost)
            }
        }
    }
}
