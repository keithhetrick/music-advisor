import SwiftUI
import MAStyle

struct NavigationRail: View {
    @Binding var selection: AppTab
    var isDarkTheme: Bool = false
    var followSystemTheme: Bool = true
    var onToggleTheme: (() -> Void)? = nil
    var onSettings: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: MAStyle.Spacing.sm) {
            ForEach([AppTab.run, AppTab.history, AppTab.style], id: \.self) { tab in
                Button {
                    selection = tab
                } label: {
                    Image(systemName: icon(for: tab))
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(selection == tab ? MAStyle.ColorToken.primary : MAStyle.ColorToken.muted)
                        .padding(8)
                        .frame(maxWidth: .infinity)
                        .background(
                            Capsule()
                                .fill(selection == tab ? MAStyle.ColorToken.panel.opacity(0.5) : Color.clear)
                        )
                }
                .buttonStyle(.plain)
                .accessibilityLabel(label(for: tab))
                .help(label(for: tab))
                .contentShape(Rectangle())
                .onHover { hover in
                    if hover && selection != tab {
                        NSCursor.pointingHand.push()
                    } else if selection != tab {
                        NSCursor.pop()
                    }
                }
            }
            Spacer()
            if let onToggleTheme {
                Button(action: onToggleTheme) {
                    Image(systemName: followSystemTheme ? "circle.lefthalf.filled" : (isDarkTheme ? "moon.fill" : "sun.max.fill"))
                        .font(.system(size: 13, weight: .regular))
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .padding(8)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(followSystemTheme ? "Follow system theme" : "Toggle theme")
                .help(followSystemTheme ? "Following system appearance" : "Toggle theme")
            }
            if let onSettings {
                Button(action: onSettings) {
                    Image(systemName: "gearshape")
                        .font(.system(size: 13, weight: .regular))
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .padding(8)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Settings")
                .help("Settings")
            }
        }
        .padding(.vertical, MAStyle.Spacing.md)
        .padding(.horizontal, MAStyle.Spacing.xs)
        .frame(width: 32)
        .background(MAStyle.ColorToken.panel.opacity(0.2))
        .cornerRadius(MAStyle.Radius.md)
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
