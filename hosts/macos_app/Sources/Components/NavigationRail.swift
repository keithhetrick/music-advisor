import SwiftUI
import MAStyle

struct NavigationRail: View {
    @Binding var selection: AppTab

    var body: some View {
        VStack(spacing: MAStyle.Spacing.md) {
            ForEach([AppTab.run, AppTab.history, AppTab.style], id: \.self) { tab in
                Button {
                    selection = tab
                } label: {
                    VStack(spacing: MAStyle.Spacing.xs) {
                        Image(systemName: icon(for: tab))
                            .font(.system(size: 18, weight: .semibold))
                        Text(label(for: tab))
                            .font(MAStyle.Typography.body)
                            .minimumScaleFactor(0.85)
                            .lineLimit(1)
                            .frame(maxWidth: .infinity)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, MAStyle.Spacing.sm)
                    .padding(.vertical, MAStyle.Spacing.xs)
                    .background(selection == tab ? MAStyle.ColorToken.panel.opacity(0.6) : Color.clear)
                    .cornerRadius(MAStyle.Radius.md)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(label(for: tab))
            }
            Spacer()
        }
        .padding(.horizontal, MAStyle.Spacing.sm)
        .padding(.vertical, MAStyle.Spacing.md)
        .background(
            LinearGradient(
                colors: [
                    MAStyle.ColorToken.panel.opacity(0.75),
                    MAStyle.ColorToken.panel.opacity(0.55)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .cornerRadius(MAStyle.Radius.md)
        .shadow(color: .black.opacity(0.28), radius: 12, x: 0, y: 10)
    }

    private func icon(for tab: AppTab) -> String {
        switch tab {
        case .run: return "bolt.fill"
        case .history: return "clock.arrow.circlepath"
        case .style: return "terminal"
        }
    }

    private func label(for tab: AppTab) -> String {
        switch tab {
        case .run: return "Run"
        case .history: return "History"
        case .style: return "Chat"
        }
    }
}
