import SwiftUI

public enum MAStyle {
    // Theme is fully tokenized; swap MAStyle.theme to reskin or to a darkTheme.
    public struct Theme {
        public let colors: ColorTokens
        public let spacing: SpacingTokens
        public let radius: RadiusTokens
        public let typography: TypographyTokens
        public let shadows: ShadowTokens
        public let borders: BorderTokens
    }

    public struct ColorTokens {
        public let background: Color
        public let panel: Color
        public let border: Color
        public let primary: Color
        public let success: Color
        public let warning: Color
        public let danger: Color
        public let info: Color
        public let muted: Color
        public let metricBG: Color
    }

    public struct SpacingTokens {
        public let xs: CGFloat
        public let sm: CGFloat
        public let md: CGFloat
        public let lg: CGFloat
        public let xl: CGFloat
        public let xxl: CGFloat
    }

    public struct RadiusTokens {
        public let sm: CGFloat
        public let md: CGFloat
        public let lg: CGFloat
        public let pill: CGFloat
    }

    public struct TypographyTokens {
        public let bodyMono: Font
        public let body: Font
        public let caption: Font
        public let headline: Font
        public let title: Font
    }

    public struct Shadow {
        public let color: Color
        public let radius: CGFloat
        public let x: CGFloat
        public let y: CGFloat
    }

    public struct ShadowTokens {
        public let sm: Shadow
        public let md: Shadow
    }

    public struct BorderTokens {
        public let thin: CGFloat
        public let regular: CGFloat
    }

    // Default theme (dark-forward, neon-accented)
    private static let defaultDark = Theme(
        colors: ColorTokens(
            background: Color(red: 0.04, green: 0.05, blue: 0.08),     // deeper midnight
            panel: Color(red: 0.08, green: 0.09, blue: 0.14),          // luxury charcoal
            border: Color.white.opacity(0.12),
            primary: Color(red: 0.16, green: 0.78, blue: 0.72),        // elegant teal
            success: Color(red: 0.38, green: 0.90, blue: 0.60),
            warning: Color(red: 0.96, green: 0.70, blue: 0.36),
            danger: Color(red: 0.90, green: 0.32, blue: 0.46),
            info: Color(red: 0.48, green: 0.68, blue: 0.96),
            muted: Color.white.opacity(0.82),
            metricBG: Color.white.opacity(0.08)
        ),
        spacing: SpacingTokens(xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 28),
        radius: RadiusTokens(sm: 6, md: 10, lg: 14, pill: 999),
        typography: TypographyTokens(
            bodyMono: Font.system(size: 13, weight: .regular, design: .monospaced),
            body: Font.system(size: 14, weight: .regular),
            caption: Font.system(size: 12, weight: .regular),
            headline: Font.system(size: 16, weight: .semibold),
            title: Font.system(size: 20, weight: .semibold)
        ),
        shadows: ShadowTokens(
            sm: Shadow(color: Color.black.opacity(0.30), radius: 10, x: 0, y: 6),
            md: Shadow(color: Color.black.opacity(0.42), radius: 18, x: 0, y: 10)
        ),
        borders: BorderTokens(thin: 1, regular: 1.5)
    )

    public static var theme = defaultDark

    // Optional light theme (if needed)
    public static let darkTheme = defaultDark

    public enum ColorToken {
        public static var background: Color { MAStyle.theme.colors.background }
        public static var panel: Color { MAStyle.theme.colors.panel }
        public static var border: Color { MAStyle.theme.colors.border }
        public static var primary: Color { MAStyle.theme.colors.primary }
        public static var success: Color { MAStyle.theme.colors.success }
        public static var warning: Color { MAStyle.theme.colors.warning }
        public static var danger: Color { MAStyle.theme.colors.danger }
        public static var info: Color { MAStyle.theme.colors.info }
        public static var muted: Color { MAStyle.theme.colors.muted }
        public static var metricBG: Color { MAStyle.theme.colors.metricBG }
    }

    public enum Spacing {
        public static var xs: CGFloat { MAStyle.theme.spacing.xs }
        public static var sm: CGFloat { MAStyle.theme.spacing.sm }
        public static var md: CGFloat { MAStyle.theme.spacing.md }
        public static var lg: CGFloat { MAStyle.theme.spacing.lg }
        public static var xl: CGFloat { MAStyle.theme.spacing.xl }
        public static var xxl: CGFloat { MAStyle.theme.spacing.xxl }
    }

    public enum Radius {
        public static var sm: CGFloat { MAStyle.theme.radius.sm }
        public static var md: CGFloat { MAStyle.theme.radius.md }
        public static var lg: CGFloat { MAStyle.theme.radius.lg }
        public static var pill: CGFloat { MAStyle.theme.radius.pill }
    }

    public enum Typography {
        public static var bodyMono: Font { MAStyle.theme.typography.bodyMono }
        public static var body: Font { MAStyle.theme.typography.body }
        public static var caption: Font { MAStyle.theme.typography.caption }
        public static var headline: Font { MAStyle.theme.typography.headline }
        public static var title: Font { MAStyle.theme.typography.title }
    }

    public enum Shadows {
        public static var sm: Shadow { MAStyle.theme.shadows.sm }
        public static var md: Shadow { MAStyle.theme.shadows.md }
    }

    public enum Borders {
        public static var thin: CGFloat { MAStyle.theme.borders.thin }
        public static var regular: CGFloat { MAStyle.theme.borders.regular }
    }

    public struct Card: ViewModifier {
        var padding: CGFloat = Spacing.sm
        public func body(content: Content) -> some View {
            content
                .padding(padding)
                .background(
                    ZStack {
                        LinearGradient(
                            colors: [
                                ColorToken.panel.opacity(0.98),
                                ColorToken.panel.opacity(0.72)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        // Subtle inner glow to lift the surface.
                        RoundedRectangle(cornerRadius: Radius.md)
                            .stroke(Color.white.opacity(0.06), lineWidth: 1)
                            .blur(radius: 1.2)
                            .blendMode(.screen)
                        // Light sheen across the top.
                        LinearGradient(
                            colors: [
                                Color.white.opacity(0.10),
                                Color.white.opacity(0.02)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        .mask(
                            RoundedRectangle(cornerRadius: Radius.md)
                                .padding(.top, 2)
                        )
                    }
                )
                .cornerRadius(Radius.md)
                .overlay(
                    // Dual-tone border for depth.
                    RoundedRectangle(cornerRadius: Radius.md)
                        .stroke(
                            LinearGradient(
                                colors: [
                                    Color.white.opacity(0.10),
                                    ColorToken.border
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: Borders.thin
                        )
                )
                // Inner shadow for depth.
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.md)
                        .stroke(Color.black.opacity(0.25), lineWidth: 1)
                        .blur(radius: 4)
                        .offset(y: 2)
                        .mask(
                            RoundedRectangle(cornerRadius: Radius.md)
                        )
                )
                // Layered shadows for 3D lift with a soft accent halo.
                .shadow(color: Color.black.opacity(0.42), radius: 18, x: 0, y: 12)
                .shadow(color: ColorToken.primary.opacity(0.12), radius: 26, x: 0, y: 18)
        }
    }

    public struct MetricBadge: ViewModifier {
        public func body(content: Content) -> some View {
            content
                .padding(Spacing.sm)
                .background(
                    LinearGradient(
                        colors: [
                            ColorToken.metricBG.opacity(0.92),
                            ColorToken.metricBG.opacity(0.62)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .cornerRadius(Radius.md)
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.md)
                        .stroke(
                            LinearGradient(
                                colors: [
                                    Color.white.opacity(0.10),
                                    ColorToken.border
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: Borders.thin
                        )
                )
                .overlay(
                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.12),
                            Color.clear
                        ],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                    .mask(RoundedRectangle(cornerRadius: Radius.md))
                )
                .shadow(color: Color.black.opacity(0.30), radius: 12, x: 0, y: 8)
        }
    }

    public struct Sheen: ViewModifier {
        @State private var phase: CGFloat = -1.2
        var isActive: Bool = true
        var duration: Double = 5.5
        var angle: Angle = .degrees(18)
        var highlight: Color = Color.white.opacity(0.16)

        public func body(content: Content) -> some View {
            content
                .overlay(
                    Group {
                        if isActive {
                            GeometryReader { geo in
                                let width = geo.size.width
                                Rectangle()
                                    .fill(
                                        LinearGradient(
                                            colors: [
                                                Color.clear,
                                                highlight,
                                                Color.clear
                                            ],
                                            startPoint: .top,
                                            endPoint: .bottom
                                        )
                                    )
                                    .frame(width: width * 0.35)
                                    .rotationEffect(angle)
                                    .offset(x: phase * width * 1.2)
                                    .blendMode(.screen)
                                    .onAppear {
                                        withAnimation(.linear(duration: duration).repeatForever(autoreverses: false)) {
                                            phase = 1.4
                                        }
                                    }
                            }
                        }
                    }
                )
        }
    }

    public struct ButtonStyle: ViewModifier {
        public enum Variant { case primary, secondary, ghost }
        public var variant: Variant = .primary
        @ViewBuilder
        public func body(content: Content) -> some View {
            let base = content
                .font(Typography.body)
                .padding(.vertical, Spacing.sm)
                .padding(.horizontal, Spacing.md)
                .cornerRadius(Radius.md)
            switch variant {
            case .primary:
                base
                    .background(
                        LinearGradient(
                            colors: [
                                ColorToken.primary.opacity(0.95),
                                ColorToken.primary.opacity(0.80)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .foregroundColor(.white)
                    // Tighter, richer shadow for a premium pill look.
                    .shadow(color: Color.black.opacity(0.35), radius: 12, x: 0, y: 6)
                    .shadow(color: ColorToken.primary.opacity(0.20), radius: 16, x: 0, y: 10)
            case .secondary:
                base
                    .background(ColorToken.panel)
                    .overlay(RoundedRectangle(cornerRadius: Radius.md).stroke(ColorToken.border, lineWidth: Borders.thin))
                    .foregroundColor(ColorToken.primary)
            case .ghost:
                base
                    .foregroundColor(ColorToken.primary)
            }
        }
    }

    public struct TextStyle: ViewModifier {
        public enum Kind { case title, headline, body, mono, caption }
        public var kind: Kind
        public func body(content: Content) -> some View {
            switch kind {
            case .title: return content.font(Typography.title)
            case .headline: return content.font(Typography.headline)
            case .body: return content.font(Typography.body)
            case .mono: return content.font(Typography.bodyMono)
            case .caption: return content.font(Typography.caption)
            }
        }
    }

    public struct Padding: ViewModifier {
        var top: CGFloat
        var leading: CGFloat
        var bottom: CGFloat
        var trailing: CGFloat
        public func body(content: Content) -> some View {
            content.padding(EdgeInsets(top: top, leading: leading, bottom: bottom, trailing: trailing))
        }
    }

    public struct Margin: ViewModifier {
        var top: CGFloat
        var leading: CGFloat
        var bottom: CGFloat
        var trailing: CGFloat
        public func body(content: Content) -> some View {
            content.padding(EdgeInsets(top: top, leading: leading, bottom: bottom, trailing: trailing))
        }
    }

    public struct Chip: ViewModifier {
        public enum Style { case solid, outline }
        public var style: Style = .solid
        public var color: Color = ColorToken.primary
        public func body(content: Content) -> some View {
            let base = content
                .font(Typography.caption)
                .padding(.horizontal, Spacing.sm)
                .padding(.vertical, Spacing.xs)
                .cornerRadius(Radius.pill)
            switch style {
            case .solid:
                base
                    .background(color.opacity(0.15))
                    .foregroundColor(color)
            case .outline:
                base
                    .overlay(RoundedRectangle(cornerRadius: Radius.pill).stroke(color, lineWidth: Borders.thin))
                    .foregroundColor(color)
            }
        }
    }

    public struct Badge: ViewModifier {
        public enum Tone { case info, success, warning, danger, neutral }
        public var tone: Tone = .neutral
        private var toneColor: Color {
            switch tone {
            case .info: return ColorToken.info
            case .success: return ColorToken.success
            case .warning: return ColorToken.warning
            case .danger: return ColorToken.danger
            case .neutral: return ColorToken.muted
            }
        }
        public func body(content: Content) -> some View {
            content
                .font(Typography.caption)
                .padding(.horizontal, Spacing.sm)
                .padding(.vertical, Spacing.xs)
                .background(toneColor.opacity(0.12))
                .foregroundColor(toneColor)
                .cornerRadius(Radius.pill)
        }
    }

    public static func useDarkTheme() { theme = darkTheme }
    public static func useLightTheme(_ light: Theme? = nil) {
        if let light { theme = light } else {
            // Recreate the default light theme (since theme is mutable).
            theme = Theme(
                colors: ColorTokens(
                    background: Color(nsColor: .windowBackgroundColor),
                    panel: Color(nsColor: NSColor(calibratedWhite: 0.95, alpha: 1)),
                    border: Color.secondary.opacity(0.16),
                    primary: Color(red: 0.18, green: 0.55, blue: 0.85),
                    success: Color.green,
                    warning: Color.orange,
                    danger: Color.red,
                    info: Color.blue,
                    muted: Color.secondary.opacity(0.8),
                    metricBG: Color.secondary.opacity(0.08)
                ),
                spacing: SpacingTokens(xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 28),
                radius: RadiusTokens(sm: 6, md: 10, lg: 14, pill: 999),
                typography: TypographyTokens(
                    bodyMono: Font.system(.body, design: .monospaced),
                    body: Font.body,
                    caption: Font.caption,
                    headline: Font.headline,
                    title: Font.title
                ),
                shadows: ShadowTokens(
                    sm: Shadow(color: Color.black.opacity(0.10), radius: 6, x: 0, y: 3),
                    md: Shadow(color: Color.black.opacity(0.16), radius: 12, x: 0, y: 6)
                ),
                borders: BorderTokens(thin: 1, regular: 1.5)
            )
        }
    }
}

extension View {
    public func maCard(padding: CGFloat = MAStyle.Spacing.sm) -> some View {
        modifier(MAStyle.Card(padding: padding))
    }

    public func maMetric() -> some View {
        modifier(MAStyle.MetricBadge())
    }

    public func maShadow(_ shadow: MAStyle.Shadow) -> some View {
        self.shadow(color: shadow.color, radius: shadow.radius, x: shadow.x, y: shadow.y)
    }

    public func maButton(_ variant: MAStyle.ButtonStyle.Variant = .primary) -> some View {
        modifier(MAStyle.ButtonStyle(variant: variant))
    }

    public func maText(_ kind: MAStyle.TextStyle.Kind) -> some View {
        modifier(MAStyle.TextStyle(kind: kind))
    }

    public func maPadding(_ top: CGFloat = 0, _ leading: CGFloat = 0, _ bottom: CGFloat = 0, _ trailing: CGFloat = 0) -> some View {
        modifier(MAStyle.Padding(top: top, leading: leading, bottom: bottom, trailing: trailing))
    }

    public func maMargin(_ top: CGFloat = 0, _ leading: CGFloat = 0, _ bottom: CGFloat = 0, _ trailing: CGFloat = 0) -> some View {
        modifier(MAStyle.Margin(top: top, leading: leading, bottom: bottom, trailing: trailing))
    }

    public func maChip(style: MAStyle.Chip.Style = .solid, color: Color = MAStyle.ColorToken.primary) -> some View {
        modifier(MAStyle.Chip(style: style, color: color))
    }

    public func maBadge(_ tone: MAStyle.Badge.Tone = .neutral) -> some View {
        modifier(MAStyle.Badge(tone: tone))
    }

    public func maSheen(isActive: Bool = true, duration: Double = 5.5, highlight: Color = Color.white.opacity(0.16)) -> some View {
        modifier(MAStyle.Sheen(isActive: isActive, duration: duration, highlight: highlight))
    }
}
