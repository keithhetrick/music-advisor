import SwiftUI
import MAStyle

/// Lightweight adapter to keep MAStyle usage consistent and provide local aliases.
enum AppTheme {
    static func apply(isDark: Bool) {
        if isDark {
            MAStyle.useDarkTheme()
        } else {
            MAStyle.useLightTheme()
        }
    }

    enum Spacing {
        static let xs = MAStyle.Spacing.xs
        static let sm = MAStyle.Spacing.sm
        static let md = MAStyle.Spacing.md
        static let lg = MAStyle.Spacing.lg
    }

    enum Radius {
        static let sm = MAStyle.Radius.sm
        static let md = MAStyle.Radius.md
        static let lg = MAStyle.Radius.lg
    }

    enum ColorToken {
        static let background = MAStyle.ColorToken.background
        static let panel = MAStyle.ColorToken.panel
        static let border = MAStyle.ColorToken.border
        static let primary = MAStyle.ColorToken.primary
        static let info = MAStyle.ColorToken.info
        static let muted = MAStyle.ColorToken.muted
    }

    enum Typography {
        static let body = MAStyle.Typography.body
        static let headline = MAStyle.Typography.headline
        static let caption = MAStyle.Typography.caption
    }
}
