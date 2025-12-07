import SwiftUI

public struct MABreadcrumb: Identifiable {
    public let id = UUID()
    public let title: String
    public let action: (() -> Void)?
    public init(_ title: String, action: (() -> Void)? = nil) {
        self.title = title
        self.action = action
    }
}

public struct MABreadcrumbs: View {
    let items: [MABreadcrumb]
    public init(_ items: [MABreadcrumb]) {
        self.items = items
    }
    public var body: some View {
        HStack(spacing: MAStyle.Spacing.xs) {
            ForEach(Array(items.enumerated()), id: \.offset) { idx, item in
                if let action = item.action {
                    Button(action: action) {
                        Text(item.title)
                            .font(MAStyle.Typography.caption)
                    }
                    .buttonStyle(MAStyle.InteractiveButtonStyle(variant: .ghost))
                } else {
                    Text(item.title)
                        .font(MAStyle.Typography.caption)
                        .foregroundColor(MAStyle.ColorToken.muted)
                }
                if idx < items.count - 1 {
                    MAIcon("chevron.right", size: 10, weight: .semibold, color: MAStyle.ColorToken.border)
                }
            }
        }
        .padding(.vertical, MAStyle.Spacing.xs)
        .padding(.horizontal, MAStyle.Spacing.sm)
        .background(MAStyle.ColorToken.panel.opacity(0.4))
        .cornerRadius(MAStyle.Radius.sm)
    }
}
