import SwiftUI

enum MAStyle {
    enum ColorToken {
        static let background = Color(nsColor: .windowBackgroundColor)
        static let panel = Color(nsColor: NSColor(calibratedWhite: 0.97, alpha: 1))
        static let border = Color.secondary.opacity(0.2)
        static let primary = Color.accentColor
        static let success = Color.green
        static let warning = Color.orange
        static let danger = Color.red
        static let info = Color.blue
        static let muted = Color.secondary
        static let metricBG = Color.secondary.opacity(0.08)
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 14
        static let lg: CGFloat = 20
    }

    enum Radius {
        static let sm: CGFloat = 6
        static let md: CGFloat = 8
    }

    enum Typography {
        static let bodyMono = Font.system(.body, design: .monospaced)
        static let body = Font.body
        static let caption = Font.caption
        static let headline = Font.headline
        static let title = Font.title
    }

    struct Card: ViewModifier {
        var padding: CGFloat = Spacing.sm
        func body(content: Content) -> some View {
            content
                .padding(padding)
                .background(ColorToken.panel)
                .cornerRadius(Radius.md)
                .overlay(RoundedRectangle(cornerRadius: Radius.md).stroke(ColorToken.border))
        }
    }

    struct MetricBadge: ViewModifier {
        func body(content: Content) -> some View {
            content
                .padding(Spacing.sm)
                .background(ColorToken.metricBG)
                .cornerRadius(Radius.md)
        }
    }
}

extension View {
    func maCard(padding: CGFloat = MAStyle.Spacing.sm) -> some View {
        modifier(MAStyle.Card(padding: padding))
    }

    func maMetric() -> some View {
        modifier(MAStyle.MetricBadge())
    }
}
