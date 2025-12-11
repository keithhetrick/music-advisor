import SwiftUI
import Combine
import AppKit

public enum MAStyle {
    // MARK: - Theme Backbone
    // All style values originate from MAStyle.theme. Swap this at runtime (useDarkTheme / useHighContrastTheme / useLightTheme)
    // or assign a custom Theme to reskin everything. The initial palette seeds live in `defaultDark.colors`.
    // Primary token container (colors/spacing/radius/typography/shadows/borders).
    public struct Theme {
        public let colors: ColorTokens
        public let spacing: SpacingTokens
        public let radius: RadiusTokens
        public let typography: TypographyTokens
        public let shadows: ShadowTokens
        public let borders: BorderTokens
    }

    // MARK: Theme Token Definitions
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

    // MARK: - Default Palette
    // This is the single source of truth for initial colors/spacing/radius/etc.
    private static let defaultDark = Theme(
        colors: ColorTokens(
            background: Color(red: 0.05, green: 0.06, blue: 0.08),     // charcoal base
            panel: Color(red: 0.10, green: 0.11, blue: 0.15),          // deep panel
            border: Color.white.opacity(0.12),
            primary: Color(red: 0.42, green: 0.64, blue: 0.82),        // crisp neutral steel
            success: Color(red: 0.42, green: 0.82, blue: 0.56),
            warning: Color(red: 0.95, green: 0.72, blue: 0.38),
            danger: Color(red: 0.88, green: 0.30, blue: 0.44),
            info: Color(red: 0.48, green: 0.68, blue: 0.96),
            muted: Color.white.opacity(0.84),
            metricBG: Color.white.opacity(0.08)
        ),
        spacing: SpacingTokens(xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 28),
        radius: RadiusTokens(sm: 6, md: 10, lg: 14, pill: 999),
        typography: TypographyTokens(
            bodyMono: Font.system(size: 13, weight: .regular, design: .monospaced),
            body: Font.system(size: 15, weight: .regular),
            caption: Font.system(size: 12, weight: .regular),
            headline: Font.system(size: 17, weight: .semibold),
            title: Font.system(size: 22, weight: .semibold)
        ),
        shadows: ShadowTokens(
            sm: Shadow(color: Color.black.opacity(0.28), radius: 10, x: 0, y: 6),
            md: Shadow(color: Color.black.opacity(0.36), radius: 16, x: 0, y: 10)
        ),
        borders: BorderTokens(thin: 1, regular: 1.4)
    )

    /// Global theme state. Swap to a different Theme to reskin; defaults to `defaultDark`.
    /// All ColorToken/Spacing/etc. values read from this.
    public static var theme = defaultDark
    public static var reduceMotionEnabled: Bool = false

    // Optional light theme (if needed)
    public static let darkTheme = defaultDark
    public static let highContrastTheme: Theme = Theme(
        colors: ColorTokens(
            background: Color(red: 0.02, green: 0.02, blue: 0.05),
            panel: Color(red: 0.06, green: 0.07, blue: 0.12),
            border: Color.white.opacity(0.2),
            primary: Color(red: 0.12, green: 0.9, blue: 0.8),
            success: Color(red: 0.45, green: 0.95, blue: 0.65),
            warning: Color(red: 1.0, green: 0.75, blue: 0.35),
            danger: Color(red: 1.0, green: 0.35, blue: 0.5),
            info: Color(red: 0.55, green: 0.75, blue: 1.0),
            muted: Color.white,
            metricBG: Color.white.opacity(0.12)
        ),
        spacing: SpacingTokens(xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 28),
        radius: RadiusTokens(sm: 6, md: 10, lg: 14, pill: 999),
        typography: TypographyTokens(
            bodyMono: Font.system(size: 13, weight: .regular, design: .monospaced),
            body: Font.system(size: 14, weight: .medium),
            caption: Font.system(size: 12, weight: .semibold),
            headline: Font.system(size: 16, weight: .semibold),
            title: Font.system(size: 20, weight: .bold)
        ),
        shadows: ShadowTokens(
            sm: Shadow(color: Color.black.opacity(0.45), radius: 12, x: 0, y: 7),
            md: Shadow(color: Color.black.opacity(0.55), radius: 20, x: 0, y: 12)
        ),
        borders: BorderTokens(thin: 1.2, regular: 1.6)
    )

    // MARK: - Global Defaults
    /// Toast defaults live here so changing once updates app-wide behavior.
    public enum ToastDefaults {
        public static var autoDismissSeconds: Double = 8.0
        public static var slideOffset: CGFloat = 24.0
        public static var collapseScaleX: CGFloat = 0.88
        public static var dismissSpring: (response: Double, damping: Double) = (0.6, 0.88)
    }

    // MARK: - Token Accessors
    // These pull directly from the active `MAStyle.theme`; swap the theme to change all values globally.
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

    // MARK: - Core Modifiers / Components
    public struct Card: ViewModifier {
        var padding: CGFloat = Spacing.sm
        var isDisabled: Bool = false
        var isInteractive: Bool = false
        var enableLens: Bool = false
        @State private var hovering = false

        public func body(content: Content) -> some View {
            let corner: CGFloat = Radius.lg * 1.5
            let base = content
                .padding(padding)
                .background(
                    ZStack {
                        // Frosted material with a soft tint.
                        VisualEffectBlur(material: .menu, blendingMode: .withinWindow)
                            .clipShape(RoundedRectangle(cornerRadius: corner))
                            .blur(radius: 24)
                        Color.white.opacity(0.015) // light veil for clarity
                            .clipShape(RoundedRectangle(cornerRadius: corner))
                        LinearGradient(
                            colors: [
                                Color.white.opacity(0.04),
                                ColorToken.panel.opacity(0.10),
                                ColorToken.primary.opacity(0.03)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        .clipShape(RoundedRectangle(cornerRadius: corner))
                        if enableLens {
                            OrganicLensOverlay(intensity: 0.05, scale: 1.15, highlight: 0.08)
                                .clipShape(RoundedRectangle(cornerRadius: corner))
                                .blendMode(.screen)
                        }
                        // Soft top highlight to suggest ambient light.
                        LinearGradient(
                            colors: [
                                Color.white.opacity(0.06),
                                Color.clear
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                        .clipShape(RoundedRectangle(cornerRadius: corner))
                    }
                    .opacity(0.70)
                )
                .cornerRadius(corner)
                .overlay(
                    RoundedRectangle(cornerRadius: corner)
                        .stroke(ColorToken.border, lineWidth: Borders.thin)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: corner)
                        .stroke(Color.white.opacity(0.06), lineWidth: 1)
                        .blendMode(.screen)
                )
                // Inset feel: light inner highlight bottom/right, soft inner shadow top/left.
                .overlay(
                    RoundedRectangle(cornerRadius: corner)
                        .stroke(
                            LinearGradient(
                                colors: [
                                    Color.black.opacity(0.06),
                                    Color.clear,
                                    Color.white.opacity(0.05)
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1.3
                        )
                )
                // Softer outer shadow so the glass sits over the darker backdrop.
                // Dual shadow for outward lift: tight contact + broad lift.
                .shadow(color: Color.black.opacity(0.12), radius: 8, x: 0, y: 4)
                .shadow(color: ColorToken.primary.opacity(0.12), radius: 22, x: 0, y: 12)
                // Subtle inner shadow at bottom edge for added depth.
                .overlay(
                    RoundedRectangle(cornerRadius: corner)
                        .stroke(
                            LinearGradient(
                                colors: [
                                    Color.clear,
                                    Color.black.opacity(0.04)
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            ),
                            lineWidth: 1.2
                        )
                )
                .opacity(isDisabled ? 0.6 : 1.0)

            return base
                .scaleEffect(isInteractive && hovering ? 1.005 : 1.0)
                .rotation3DEffect(
                    .degrees(isInteractive && hovering ? 1 : 0),
                    axis: (x: 1, y: -1, z: 0),
                    perspective: 0.8
                )
                .animation(.easeOut(duration: 0.10), value: hovering)
                .onHover { hovering = $0 && isInteractive && !isDisabled }
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

    public struct InteractiveButtonStyle: ButtonStyle {
        public enum Variant { case primary, secondary, ghost, busy }
        public var variant: Variant = .primary
        public var hoverScale: CGFloat = 1.02
        public var isBusy: Bool = false

        public func makeBody(configuration: Configuration) -> some View {
            HoverButton(configuration: configuration, variant: variant, hoverScale: hoverScale, isBusy: isBusy)
        }

        private struct HoverButton: View {
            let configuration: Configuration
            let variant: Variant
            let hoverScale: CGFloat
            let isBusy: Bool
            @State private var hovering = false

            var body: some View {
                let base = configuration.label
                    .font(MAStyle.Typography.body)
                    .padding(.vertical, MAStyle.Spacing.sm)
                    .padding(.horizontal, MAStyle.Spacing.md)
                    .cornerRadius(MAStyle.Radius.md)

                let styled: AnyView = {
                    switch variant {
                    case .primary, .busy:
                        return AnyView(
                            base
                                .background(
                                    LinearGradient(
                                        colors: [
                                            MAStyle.ColorToken.primary.opacity(0.95),
                                            MAStyle.ColorToken.primary.opacity(0.80)
                                        ],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                                .foregroundColor(.white)
                                .shadow(color: Color.black.opacity(0.25), radius: 10, x: 0, y: 5)
                                .shadow(color: MAStyle.ColorToken.primary.opacity(0.16), radius: 12, x: 0, y: 8)
                        )
                    case .secondary:
                        return AnyView(
                            base
                                .background(MAStyle.ColorToken.panel)
                                .overlay(RoundedRectangle(cornerRadius: MAStyle.Radius.md).stroke(MAStyle.ColorToken.border, lineWidth: MAStyle.Borders.thin))
                                .foregroundColor(MAStyle.ColorToken.primary)
                        )
                    case .ghost:
                        return AnyView(
                            base
                                .foregroundColor(MAStyle.ColorToken.primary)
                        )
                    }
                }()

                return styled
                    // Minimal sheen; avoid heavy bubble effect.
                    .overlay {
                        if hovering || configuration.isPressed {
                            RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                                .stroke(Color.white.opacity(0.08), lineWidth: 0.6)
                                .blendMode(.screen)
                        }
                    }
                    .overlay(alignment: .leading) {
                        if variant == .busy && isBusy {
                            ProgressView()
                                .progressViewStyle(.circular)
                                .scaleEffect(0.6)
                                .padding(.leading, MAStyle.Spacing.xs)
                        }
                    }
                    .overlay(
                        RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                            .stroke(focusGlow(configuration), lineWidth: focusGlowWidth(configuration))
                            .opacity(configuration.isPressed ? 0.7 : (hovering ? 0.5 : 0.35))
                    )
                    .opacity(configuration.isPressed ? 0.88 : (isBusy ? 0.85 : 1.0))
                    .scaleEffect(configuration.isPressed ? 0.98 : (hovering ? hoverScale : 1.0))
                    .animation(.spring(response: 0.18, dampingFraction: 0.8), value: configuration.isPressed)
                    .animation(.easeOut(duration: 0.12), value: hovering)
                    .onHover { hovering = $0 }
                    .disabled(isBusy)
            }

            private func focusGlow(_ configuration: Configuration) -> Color {
                switch variant {
                case .primary, .busy:
                    return MAStyle.ColorToken.primary.opacity(configuration.isPressed ? 0.4 : 0.3)
                case .secondary:
                    return MAStyle.ColorToken.primary.opacity(0.28)
                case .ghost:
                    return MAStyle.ColorToken.border.opacity(0.22)
                }
            }

            private func focusGlowWidth(_ configuration: Configuration) -> CGFloat {
                configuration.isPressed ? 2.2 : 1.6
            }
        }
    }

    public struct TextStyle: ViewModifier {
        public enum Kind { case title, headline, body, mono, caption }
        public var kind: Kind
        public func body(content: Content) -> some View {
            switch kind {
            case .title:
                return content.font(Typography.title)
                    .foregroundColor(ColorToken.muted.opacity(1.0))
            case .headline:
                return content.font(Typography.headline)
                    .foregroundColor(ColorToken.muted.opacity(1.0))
            case .body:
                return content.font(Typography.body)
                    .foregroundColor(ColorToken.muted.opacity(1.0))
            case .mono:
                return content.font(Typography.bodyMono)
                    .foregroundColor(ColorToken.muted.opacity(0.95))
            case .caption:
                return content.font(Typography.caption)
                    .foregroundColor(ColorToken.muted.opacity(0.94))
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
        public var isDisabled: Bool = false
        @State private var hovering = false
        public func body(content: Content) -> some View {
            let base = content
                .font(Typography.caption)
                .padding(.horizontal, Spacing.sm)
                .padding(.vertical, Spacing.xs)
                .cornerRadius(Radius.pill)
                .opacity(isDisabled ? 0.5 : 1.0)
            let styled: AnyView = {
                switch style {
                case .solid:
                    return AnyView(
                        base
                            .background(color.opacity(isDisabled ? 0.10 : 0.15))
                            .foregroundColor(color)
                    )
                case .outline:
                    return AnyView(
                        base
                            .overlay(RoundedRectangle(cornerRadius: Radius.pill).stroke(color, lineWidth: Borders.thin))
                            .foregroundColor(color)
                    )
                }
            }()
            return styled
                .scaleEffect(isDisabled ? 1.0 : (hovering ? 1.03 : 1.0))
                .animation(.easeOut(duration: 0.12), value: hovering)
                .onHover { hovering = $0 && !isDisabled }
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

    public struct InputField: ViewModifier {
        public enum State { case normal, error, disabled }
        var state: State = .normal
        public func body(content: Content) -> some View {
            content
                .disabled(state == .disabled)
                .padding(.vertical, Spacing.xs)
                .padding(.horizontal, Spacing.sm)
                .background(ColorToken.panel.opacity(state == .disabled ? 0.3 : 0.5))
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.sm)
                        .stroke(borderColor, lineWidth: Borders.thin)
                )
                .cornerRadius(Radius.sm)
                .opacity(state == .disabled ? 0.6 : 1.0)
        }
        private var borderColor: Color {
            switch state {
            case .normal: return ColorToken.border
            case .error: return ColorToken.danger.opacity(0.8)
            case .disabled: return ColorToken.border.opacity(0.5)
            }
        }
    }

    public struct TextArea: ViewModifier {
        var state: InputField.State = .normal
        public func body(content: Content) -> some View {
            content
                .disabled(state == .disabled)
                .padding(Spacing.sm)
                .background(ColorToken.panel.opacity(state == .disabled ? 0.3 : 0.5))
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.sm)
                        .stroke(borderColor, lineWidth: Borders.thin)
                )
                .cornerRadius(Radius.sm)
                .font(Typography.bodyMono)
                .opacity(state == .disabled ? 0.6 : 1.0)
        }
        private var borderColor: Color {
            switch state {
            case .normal: return ColorToken.border
            case .error: return ColorToken.danger.opacity(0.8)
            case .disabled: return ColorToken.border.opacity(0.5)
            }
        }
    }

    public struct PickerStyleModifier: ViewModifier {
        public func body(content: Content) -> some View {
            content
                .padding(.horizontal, Spacing.sm)
                .padding(.vertical, Spacing.xs)
                .background(ColorToken.panel.opacity(0.6))
                .overlay(RoundedRectangle(cornerRadius: Radius.sm).stroke(ColorToken.border, lineWidth: Borders.thin))
                .cornerRadius(Radius.sm)
        }
    }

    public struct ProgressStyleModifier: ViewModifier {
        public func body(content: Content) -> some View {
            content
                .tint(ColorToken.primary)
                .padding(.vertical, Spacing.xs)
        }
    }

    public struct ListRowStyleModifier: ViewModifier {
        @State private var hovering = false
        public var isSelected: Bool = false
        public var isDisabled: Bool = false
        public var isFocused: Bool = false
        public func body(content: Content) -> some View {
            content
                .padding(.vertical, Spacing.xs)
                .padding(.horizontal, Spacing.sm)
                .background(rowColor)
                .cornerRadius(Radius.sm)
                .opacity(isDisabled ? 0.5 : 1.0)
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.sm)
                        .stroke(isFocused ? ColorToken.primary.opacity(0.8) : Color.clear, lineWidth: isFocused ? 2 : 0)
                )
                .onHover { hovering = $0 && !isDisabled }
        }
        private var rowColor: Color {
            if isDisabled { return ColorToken.panel.opacity(0.15) }
            if isSelected { return ColorToken.primary.opacity(0.18) }
            if hovering { return ColorToken.panel.opacity(0.45) }
            return ColorToken.panel.opacity(0.3)
        }
    }

    public struct StripedRowStyleModifier: ViewModifier {
        public var index: Int
        public var isSelected: Bool = false
        public var isDisabled: Bool = false
        public var isFocused: Bool = false
        @State private var hovering = false
        public func body(content: Content) -> some View {
            content
                .padding(.vertical, Spacing.xs)
                .padding(.horizontal, Spacing.sm)
                .background(rowColor)
                .cornerRadius(Radius.sm)
                .opacity(isDisabled ? 0.5 : 1.0)
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.sm)
                        .stroke(isFocused ? ColorToken.primary.opacity(0.8) : Color.clear, lineWidth: isFocused ? 2 : 0)
                )
                .onHover { hovering = $0 && !isDisabled }
        }
        private var rowColor: Color {
            if isDisabled { return ColorToken.panel.opacity(0.12) }
            if isSelected { return ColorToken.primary.opacity(0.2) }
            if hovering { return ColorToken.panel.opacity(0.5) }
            return index % 2 == 0 ? ColorToken.panel.opacity(0.32) : ColorToken.panel.opacity(0.25)
        }
    }

    // MARK: - Backdrop
    /// Lightweight, vector-only backdrop with soft gradients for depth.
    public struct Backdrop: View {
        public var intensity: Double
        public var accent: Color

        public init(intensity: Double = 1.0, accent: Color = MAStyle.ColorToken.primary) {
            self.intensity = intensity
            self.accent = accent
        }

        public var body: some View {
            ZStack {
                LinearGradient(
                    colors: [
                        Color(red: 0.07, green: 0.10, blue: 0.12, opacity: 1.0),
                        Color(red: 0.12, green: 0.14, blue: 0.18, opacity: 1.0)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .opacity(1.0)

                RadialGradient(
                    colors: [
                        accent.opacity(0.10 * intensity),
                        accent.opacity(0.03 * intensity),
                        .clear
                    ],
                    center: .topLeading,
                    startRadius: 40,
                    endRadius: 520
                )
                .blur(radius: 60)

                RadialGradient(
                    colors: [
                        MAStyle.ColorToken.panel.opacity(0.08 * intensity),
                        MAStyle.ColorToken.background.opacity(0.03 * intensity),
                        .clear
                    ],
                    center: .bottomTrailing,
                    startRadius: 60,
                    endRadius: 640
                )
                .blur(radius: 50)

                LinearGradient(
                    colors: [
                        Color.black.opacity(0.05 * intensity),
                        Color.clear,
                        Color.black.opacity(0.04 * intensity)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .blendMode(.multiply)

                // Optional slow organic lens glow behind everything.
                OrganicLensOverlay(intensity: 0.008, scale: 1.8, speed: 18, highlight: 0.015, parallax: .zero)
                    .blendMode(.screen)
                    .allowsHitTesting(false)

                // Subtle static noise to add texture and help cards pop.
                StaticNoise(density: 180, opacity: 0.02)
                    .blendMode(.overlay)
                    .allowsHitTesting(false)
            }
        }
    }

    // Organic lens effect: drifting caustic-like highlight.
    public struct OrganicLensOverlay: View {
        @Environment(\.colorScheme) private var scheme
        public var intensity: Double
        public var scale: CGFloat
        public var speed: Double
        public var color: Color
        public var highlight: Double
        public var parallax: CGSize

        public init(intensity: Double = 0.05,
                    scale: CGFloat = 1.0,
                    speed: Double = 12.0,
                    color: Color = Color.white,
                    highlight: Double = 0.01,
                    parallax: CGSize = .zero) {
            self.intensity = intensity
            self.scale = scale
            self.speed = speed
            self.color = color
            self.highlight = highlight
            self.parallax = parallax
        }

        public var body: some View {
            GeometryReader { proxy in
                let size = min(proxy.size.width, proxy.size.height)
                TimelineView(.animation) { timeline in
                    let t = timeline.date.timeIntervalSinceReferenceDate / speed
                    let offsetX = 0.12 * sin(t * 1.1) + 0.08 * cos(t * 0.7)
                    let offsetY = 0.10 * cos(t * 0.9) + 0.06 * sin(t * 1.3)
                    let center = UnitPoint(x: 0.5 + offsetX + parallax.width, y: 0.5 + offsetY + parallax.height)
                    let baseOpacity = scheme == .dark ? intensity : intensity * 0.85

                    ZStack {
                        RadialGradient(
                            colors: [
                                color.opacity(baseOpacity),
                                color.opacity(baseOpacity * 0.45),
                                Color.clear
                            ],
                            center: center,
                            startRadius: size * 0.05,
                            endRadius: size * 0.6 * scale
                        )
                        RadialGradient(
                            colors: [
                                Color.white.opacity(highlight),
                                Color.white.opacity(highlight * 0.25),
                                Color.clear
                            ],
                            center: center,
                            startRadius: size * 0.02,
                            endRadius: size * 0.25
                        )
                    }
                }
            }
        }
    }

    /// Lightweight reproducible noise overlay for texture (no external assets).
    private struct StaticNoise: View {
        let density: Int
        let opacity: Double

        func makeGenerator() -> LCGRandomNumberGenerator {
            LCGRandomNumberGenerator(state: 0x1234_5678_9abc_def0)
        }

        var body: some View {
            Canvas { context, size in
                var rng = makeGenerator()
                let width = max(size.width, 1)
                let height = max(size.height, 1)
                for _ in 0..<density {
                    let x = Double(rng.next() % UInt64(width))
                    let y = Double(rng.next() % UInt64(height))
                    let dotSize = Double(rng.next() % 2) + 0.5
                    let rect = CGRect(x: x, y: y, width: dotSize, height: dotSize)
                    context.fill(
                        Path(rect),
                        with: .color(Color.white.opacity(opacity))
                    )
                }
            }
        }
    }

    /// Simple linear congruential generator for deterministic noise.
    private struct LCGRandomNumberGenerator: RandomNumberGenerator {
        var state: UInt64
        mutating func next() -> UInt64 {
            state = 6364136223846793005 &* state &+ 1
            return state
        }
    }

    // MARK: - Theme Helpers
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

    // MARK: - Appearance helpers
    /// Returns true when the current system appearance is dark.
    public static func systemPrefersDark() -> Bool {
        let best = NSApplication.shared.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua])
        return best == .darkAqua
    }

    /// Publisher that emits when the system appearance changes, with the current dark/light boolean.
    public static func appearanceChangePublisher() -> AnyPublisher<Bool, Never> {
        DistributedNotificationCenter.default()
            .publisher(for: Notification.Name("AppleInterfaceThemeChangedNotification"))
            .map { _ in systemPrefersDark() }
            .eraseToAnyPublisher()
    }

    /// Apply theme based on follow-system vs manual flags. Returns the effective dark/light value applied.
    @discardableResult
    public static func applyTheme(followSystem: Bool, manualDark: Bool) -> Bool {
        let systemDark = systemPrefersDark()
        let effectiveDark = followSystem ? systemDark : manualDark
        if effectiveDark {
            MAStyle.useDarkTheme()
        } else {
            MAStyle.useLightTheme()
        }
        return effectiveDark
    }

    public static func useHighContrastTheme() {
        theme = highContrastTheme
    }

    /// Adjust spacing density (e.g., compact = 0.85, regular = 1.0).
    public static func applyDensity(scale: CGFloat) {
        theme = Theme(
            colors: theme.colors,
            spacing: SpacingTokens(
                xs: theme.spacing.xs * scale,
                sm: theme.spacing.sm * scale,
                md: theme.spacing.md * scale,
                lg: theme.spacing.lg * scale,
                xl: theme.spacing.xl * scale,
                xxl: theme.spacing.xxl * scale
            ),
            radius: theme.radius,
            typography: theme.typography,
            shadows: theme.shadows,
            borders: theme.borders
                )
    }
}

// MARK: - View Extensions (syntactic sugar)
extension View {
    public func maCard(padding: CGFloat = MAStyle.Spacing.sm, enableLens: Bool = false) -> some View {
        modifier(MAStyle.Card(padding: padding, isInteractive: false, enableLens: enableLens))
    }

    public func maCardInteractive(padding: CGFloat = MAStyle.Spacing.sm, isDisabled: Bool = false, enableLens: Bool = false) -> some View {
        modifier(MAStyle.Card(padding: padding, isDisabled: isDisabled, isInteractive: true, enableLens: enableLens))
    }

    public func maMetric() -> some View {
        modifier(MAStyle.MetricBadge())
    }

    public func maShadow(_ shadow: MAStyle.Shadow) -> some View {
        self.shadow(color: shadow.color, radius: shadow.radius, x: shadow.x, y: shadow.y)
    }

    public func maButton(_ variant: MAStyle.InteractiveButtonStyle.Variant = .primary, isBusy: Bool = false) -> some View {
        self.buttonStyle(MAStyle.InteractiveButtonStyle(variant: variant, isBusy: isBusy))
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

    public func maChip(style: MAStyle.Chip.Style = .solid, color: Color = MAStyle.ColorToken.primary, isDisabled: Bool = false) -> some View {
        modifier(MAStyle.Chip(style: style, color: color, isDisabled: isDisabled))
    }

    public func maBadge(_ tone: MAStyle.Badge.Tone = .neutral) -> some View {
        modifier(MAStyle.Badge(tone: tone))
    }

    public func maSheen(isActive: Bool = true, duration: Double = 5.5, highlight: Color = Color.white.opacity(0.16)) -> some View {
        modifier(MAStyle.Sheen(isActive: isActive, duration: duration, highlight: highlight))
    }

    public func maInput(state: MAStyle.InputField.State = .normal) -> some View {
        modifier(MAStyle.InputField(state: state))
    }

    public func maTextArea(state: MAStyle.InputField.State = .normal) -> some View {
        modifier(MAStyle.TextArea(state: state))
    }

    public func maPickerStyle() -> some View {
        modifier(MAStyle.PickerStyleModifier())
    }

    public func maProgressStyle() -> some View {
        modifier(MAStyle.ProgressStyleModifier())
    }

    public func maListRowStyle(isSelected: Bool = false, isDisabled: Bool = false, isFocused: Bool = false) -> some View {
        modifier(MAStyle.ListRowStyleModifier(isSelected: isSelected, isDisabled: isDisabled, isFocused: isFocused))
    }

    public func maStripedRowStyle(index: Int, isSelected: Bool = false, isDisabled: Bool = false, isFocused: Bool = false) -> some View {
        modifier(MAStyle.StripedRowStyleModifier(index: index, isSelected: isSelected, isDisabled: isDisabled, isFocused: isFocused))
    }
}

// MARK: - Grouped Row Helper
public struct GroupedRow<Label: View>: View {
    let isActive: Bool
    let fillOpacity: Double
    let strokeOpacity: Double
    let lineWidth: CGFloat
    let content: Label
    public init(isActive: Bool,
                fillOpacity: Double = 0.08,
                strokeOpacity: Double = 0.35,
                lineWidth: CGFloat = 1.2,
                @ViewBuilder content: () -> Label) {
        self.isActive = isActive
        self.fillOpacity = fillOpacity
        self.strokeOpacity = strokeOpacity
        self.lineWidth = lineWidth
        self.content = content()
    }
    public var body: some View {
        content
            .padding(.vertical, MAStyle.Spacing.xs)
            .padding(.horizontal, MAStyle.Spacing.sm)
            .maActiveOutline(isActive: isActive,
                             cornerRadius: MAStyle.Radius.md,
                             fillOpacity: fillOpacity,
                             strokeOpacity: strokeOpacity,
                             lineWidth: lineWidth)
    }
}
