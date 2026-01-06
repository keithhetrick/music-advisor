import SwiftUI
import MAStyle

struct NavigationRail: View {
    @Binding var selection: AppTab
    var isDarkTheme: Bool = false
    var followSystemTheme: Bool = true
    var onToggleTheme: (() -> Void)? = nil
    var onSettings: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: MAStyle.Spacing.md) {
            ForEach([AppTab.library, AppTab.analyze, AppTab.results, AppTab.echo, AppTab.guide, AppTab.settings], id: \.self) { tab in
                Button {
                    selection = tab
                } label: {
                    VStack(spacing: MAStyle.Spacing.xs) {
                        Image(systemName: icon(for: tab))
                            .font(.system(size: 14, weight: .semibold))
                        Text(shortLabel(for: tab))
                            .maText(.caption)
                    }
                    .foregroundStyle(selection == tab ? DesignTokens.Color.accent : MAStyle.ColorToken.muted)
                    .padding(.vertical, MAStyle.Spacing.xs)
                    .frame(maxWidth: .infinity)
                    .background(
                        RoundedRectangle(cornerRadius: MAStyle.Radius.sm)
                            .fill(selection == tab ? DesignTokens.Color.surface.opacity(0.65) : Color.clear)
                            .overlay(
                                RoundedRectangle(cornerRadius: MAStyle.Radius.sm)
                                    .stroke(selection == tab ? DesignTokens.Color.accent.opacity(0.6) : Color.clear, lineWidth: 1)
                            )
                    )
                }
                .buttonStyle(.plain)
                .accessibilityLabel(label(for: tab))
                .accessibilityIdentifier("tab-\(label(for: tab))")
                .help(label(for: tab))
                .contentShape(Rectangle())
            }
            Divider()
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
                .accessibilityIdentifier("nav-theme-toggle")
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
                .accessibilityIdentifier("nav-settings")
                .help("Settings")
            }
        }
        .padding(.vertical, MAStyle.Spacing.md)
        .padding(.horizontal, MAStyle.Spacing.xs)
        .frame(width: 96, alignment: .top)
        .background(MAStyle.ColorToken.panel.opacity(0.32))
        .cornerRadius(MAStyle.Radius.md)
    }

    private func icon(for tab: AppTab) -> String {
        switch tab {
        case .library: return "music.note.list"
        case .analyze: return "bolt.fill"
        case .results: return "chart.bar.xaxis"
        case .echo: return "waveform.and.magnifyingglass"
        case .guide: return "questionmark.bubble"
        case .settings: return "gearshape"
        }
    }

    private func label(for tab: AppTab) -> String {
        switch tab {
        case .library: return "Library"
        case .analyze: return "Analyze"
        case .results: return "Results"
        case .echo: return "Historical Echo"
        case .guide: return "Guide"
        case .settings: return "Settings"
        }
    }

    private func shortLabel(for tab: AppTab) -> String {
        switch tab {
        case .library: return "Library"
        case .analyze: return "Analyze"
        case .results: return "Results"
        case .echo: return "Echo"
        case .guide: return "Guide"
        case .settings: return "Settings"
        }
    }
}
