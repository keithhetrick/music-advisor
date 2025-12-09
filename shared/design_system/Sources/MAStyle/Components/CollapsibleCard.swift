import SwiftUI

// MARK: - CollapsibleCard
public struct CollapsibleCard<Header: View, Content: View>: View {
    let header: () -> Header
    let content: () -> Content
    @State private var isExpanded: Bool

    public init(initiallyExpanded: Bool = true,
                @ViewBuilder header: @escaping () -> Header,
                @ViewBuilder content: @escaping () -> Content) {
        self._isExpanded = State(initialValue: initiallyExpanded)
        self.header = header
        self.content = content
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                Button {
                    withAnimation(.easeInOut) { isExpanded.toggle() }
                } label: {
                    HStack(spacing: MAStyle.Spacing.xs) {
                        Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                            .foregroundStyle(MAStyle.ColorToken.muted)
                        header()
                    }
                }
                .buttonStyle(.plain)
                Spacer()
            }
            if isExpanded {
                content()
                    .transition(.opacity.combined(with: .scale))
            }
        }
        .maCardInteractive()
    }
}
