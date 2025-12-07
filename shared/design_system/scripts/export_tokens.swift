#!/usr/bin/env swift
import Foundation
import MAStyle

let colors: [String: Any] = [
    "background": MAStyle.ColorToken.background.description,
    "panel": MAStyle.ColorToken.panel.description,
    "border": MAStyle.ColorToken.border.description,
    "primary": MAStyle.ColorToken.primary.description,
    "success": MAStyle.ColorToken.success.description,
    "warning": MAStyle.ColorToken.warning.description,
    "danger": MAStyle.ColorToken.danger.description,
    "info": MAStyle.ColorToken.info.description,
    "muted": MAStyle.ColorToken.muted.description,
    "metricBG": MAStyle.ColorToken.metricBG.description
]

let spacing: [String: Any] = [
    "xs": MAStyle.Spacing.xs,
    "sm": MAStyle.Spacing.sm,
    "md": MAStyle.Spacing.md,
    "lg": MAStyle.Spacing.lg,
    "xl": MAStyle.Spacing.xl,
    "xxl": MAStyle.Spacing.xxl
]

let radius: [String: Any] = [
    "sm": MAStyle.Radius.sm,
    "md": MAStyle.Radius.md,
    "lg": MAStyle.Radius.lg,
    "pill": MAStyle.Radius.pill
]

let theme: [String: Any] = [
    "colors": colors,
    "spacing": spacing,
    "radius": radius
]

let data = try JSONSerialization.data(withJSONObject: theme, options: [.prettyPrinted])
if let json = String(data: data, encoding: .utf8) {
    print(json)
}
