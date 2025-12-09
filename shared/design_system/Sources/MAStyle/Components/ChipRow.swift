import SwiftUI

// MARK: - Chip Row
/// Reusable horizontal chip row with optional trailing content (e.g., a FAB).
public struct ChipRow<Item: Identifiable & Hashable>: View where Item: CustomStringConvertible {
    public enum Style {
        case solid
        case outline
    }

    let items: [Item]
    let style: Style
    let spacing: CGFloat
    let trailingSpacing: CGFloat
    let trailingContent: AnyView?
    let onSelect: (Item) -> Void

    public init(
        items: [Item],
        style: Style = .solid,
        spacing: CGFloat = MAStyle.Spacing.sm,
        trailingSpacing: CGFloat = 52,
        trailingContent: AnyView? = nil,
        onSelect: @escaping (Item) -> Void
    ) {
        self.items = items
        self.style = style
        self.spacing = spacing
        self.trailingSpacing = trailingSpacing
        self.trailingContent = trailingContent
        self.onSelect = onSelect
    }

    public var body: some View {
        ZStack(alignment: .trailing) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: spacing) {
                    ForEach(items) { item in
                        Button(item.description) { onSelect(item) }
                            .buttonStyle(.plain)
                            .maChip(style: chipStyle, color: MAStyle.ColorToken.primary)
                            .accessibilityLabel("Select \(item.description)")
                }
                    // Spacer so trailing content doesn't overlap chips.
                    Color.clear.frame(width: trailingSpacing, height: 1)
                }
            }
            if let trailingContent {
                trailingContent
            }
        }
    }

    private var chipStyle: MAStyle.Chip.Style {
        switch style {
        case .solid: return .solid
        case .outline: return .outline
        }
    }
}
