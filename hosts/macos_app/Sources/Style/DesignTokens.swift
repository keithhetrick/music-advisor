import SwiftUI
import MAStyle

/// Centralized visual tokens for the rebrand. Mirrors MAStyle but locks the scale we use in-app.
enum DesignTokens {
    enum Spacing {
        static let xxs: CGFloat = 4
        static let xs: CGFloat = 8
        static let sm: CGFloat = 12
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
    }

    enum Radius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 18
    }

    enum Color {
        static let background: SwiftUI.Color = MAStyle.ColorToken.background
        static let surface: SwiftUI.Color = SwiftUI.Color.white.opacity(0.08)
        static let border: SwiftUI.Color = SwiftUI.Color.white.opacity(0.22)
        static let text: SwiftUI.Color = .primary
        static let muted: SwiftUI.Color = MAStyle.ColorToken.muted
        static let accent: SwiftUI.Color = SwiftUI.Color(red: 0.10, green: 0.60, blue: 1.0) // polished, Apple-adjacent blue
        static let success: SwiftUI.Color = MAStyle.ColorToken.success
        static let warning: SwiftUI.Color = MAStyle.ColorToken.warning
        static let danger: SwiftUI.Color = MAStyle.ColorToken.danger
    }

    enum Typography {
        static let title = MAStyle.Typography.title
        static let headline = MAStyle.Typography.headline
        static let body = MAStyle.Typography.body
        static let caption = MAStyle.Typography.caption
        static let mono = MAStyle.Typography.bodyMono
    }

    enum Shadow {
        static let medium = ShadowStyle(color: SwiftUI.Color.black.opacity(0.16), radius: 14, y: 6)
        static let subtle = ShadowStyle(color: SwiftUI.Color.black.opacity(0.06), radius: 10, y: 4)
    }

    enum Gradient {
        static let backdrop = [
            SwiftUI.Color(red: 0.05, green: 0.07, blue: 0.12),
            SwiftUI.Color(red: 0.02, green: 0.11, blue: 0.19),
            SwiftUI.Color(red: 0.01, green: 0.02, blue: 0.06)
        ]
    }

    struct ShadowStyle {
        let color: SwiftUI.Color
        let radius: CGFloat
        let y: CGFloat
    }
}

extension View {
    func cardSurface(padding: CGFloat = DesignTokens.Spacing.md, cornerRadius: CGFloat = DesignTokens.Radius.md, shadow: DesignTokens.ShadowStyle? = DesignTokens.Shadow.subtle) -> some View {
        let shape = RoundedRectangle(cornerRadius: cornerRadius)
        let base = self
            .padding(padding)
            .background(
                shape
                    .fill(.thinMaterial)
                    .overlay(
                        LinearGradient(colors: [
                            DesignTokens.Color.surface.opacity(0.36),
                            DesignTokens.Color.surface.opacity(0.18)
                        ], startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
            )
            .overlay(
                shape
                    .stroke(LinearGradient(colors: [
                        DesignTokens.Color.border.opacity(0.65),
                        DesignTokens.Color.accent.opacity(0.32)
                    ], startPoint: .topLeading, endPoint: .bottomTrailing), lineWidth: 0.8)
            )
        if let shadow {
            return AnyView(base.shadow(color: shadow.color, radius: shadow.radius, x: 0, y: shadow.y))
        }
        return AnyView(base)
    }

    func pillBackground() -> some View {
        self
            .padding(.horizontal, DesignTokens.Spacing.sm)
            .padding(.vertical, DesignTokens.Spacing.xs)
            .background(DesignTokens.Color.surface.opacity(0.65))
            .cornerRadius(DesignTokens.Radius.sm)
    }
}
