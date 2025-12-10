import SwiftUI

// MARK: - FAB + Popover Palette
/// A floating action button that opens a popover with optional search and a selectable list.
public struct FABPopover<Item: Identifiable & Hashable>: View where Item: CustomStringConvertible {
    let icon: String
    let items: [Item]
    let width: CGFloat
    let maxHeight: CGFloat
    let enableSearch: Bool
    let onSelect: (Item) -> Void
    let onClose: (() -> Void)?

    @State private var isPresented: Bool = false
    @State private var search: String = ""

    public init(
        icon: String = "text.badge.plus",
        items: [Item],
        width: CGFloat = 260,
        maxHeight: CGFloat = 240,
        enableSearch: Bool = true,
        onSelect: @escaping (Item) -> Void,
        onClose: (() -> Void)? = nil
    ) {
        self.icon = icon
        self.items = items
        self.width = width
        self.maxHeight = maxHeight
        self.enableSearch = enableSearch
        self.onSelect = onSelect
        self.onClose = onClose
    }

    public var body: some View {
        Button {
            withAnimation(.spring(response: 0.25, dampingFraction: 0.9)) {
                isPresented.toggle()
                search = ""
            }
        } label: {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .semibold))
                .padding(MAStyle.Spacing.sm)
                .background(Circle().fill(MAStyle.ColorToken.panel.opacity(0.9)))
                .overlay(Circle().stroke(MAStyle.ColorToken.border.opacity(0.35), lineWidth: MAStyle.Borders.thin))
                .shadow(color: .black.opacity(0.18), radius: 8, x: 0, y: 4)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Open snippets")
        .popover(isPresented: $isPresented, attachmentAnchor: .rect(.bounds), arrowEdge: .top) {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                HStack {
                    Text("Snippets")
                        .maText(.headline)
                    Spacer()
                    Button {
                        withAnimation { isPresented = false }
                        onClose?()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 12, weight: .semibold))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Close palette")
                }
                if enableSearch {
                    TextField("Search", text: $search)
                        .textFieldStyle(.roundedBorder)
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                        ForEach(filteredItems, id: \.self) { item in
                            Button(item.description) {
                                onSelect(item)
                                isPresented = false
                                onClose?()
                            }
                            .maButton(.ghost)
                            .accessibilityLabel("Select \(item.description)")
                        }
                    }
                }
                .frame(maxHeight: maxHeight)
            }
            .padding(MAStyle.Spacing.md)
            .frame(width: width)
            .background(MAStyle.ColorToken.panel.opacity(0.9))
        }
    }

    private var filteredItems: [Item] {
        let trimmed = search.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return items }
        return items.filter { $0.description.localizedCaseInsensitiveContains(trimmed) }
    }
}
