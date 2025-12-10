import SwiftUI

// MARK: - Icons

public struct MAIcon: View {
    let systemName: String
    let size: CGFloat
    let weight: Font.Weight
    let color: Color?

    public init(_ systemName: String, size: CGFloat = 14, weight: Font.Weight = .regular, color: Color? = nil) {
        self.systemName = systemName
        self.size = size
        self.weight = weight
        self.color = color
    }

    public var body: some View {
        Image(systemName: systemName)
            .font(.system(size: size, weight: weight))
            .foregroundColor(color ?? MAStyle.ColorToken.muted)
    }
}

public struct MATag: View {
    let text: String
    let icon: String?
    let tone: MAStyle.Badge.Tone

    public init(_ text: String, icon: String? = nil, tone: MAStyle.Badge.Tone = .neutral) {
        self.text = text
        self.icon = icon
        self.tone = tone
    }

    public var body: some View {
        HStack(spacing: MAStyle.Spacing.xs) {
            if let icon {
                MAIcon(icon, size: 11, weight: .semibold, color: toneColor)
            }
            Text(text)
                .font(MAStyle.Typography.caption)
        }
        .padding(.horizontal, MAStyle.Spacing.sm)
        .padding(.vertical, MAStyle.Spacing.xs)
        .background(toneColor.opacity(0.12))
        .foregroundColor(toneColor)
        .cornerRadius(MAStyle.Radius.pill)
    }

    private var toneColor: Color {
        switch tone {
        case .info: return MAStyle.ColorToken.info
        case .success: return MAStyle.ColorToken.success
        case .warning: return MAStyle.ColorToken.warning
        case .danger: return MAStyle.ColorToken.danger
        case .neutral: return MAStyle.ColorToken.muted
        }
    }
}

// MARK: - Layout / Background
public struct MAStackSpacing: ViewModifier {
    let spacing: CGFloat
    public func body(content: Content) -> some View {
        content
            .padding(.vertical, spacing / 2)
    }
}

public struct AppBackground: ViewModifier {
    public func body(content: Content) -> some View {
        content
            .background(
                LinearGradient(
                    colors: [
                        MAStyle.ColorToken.background,
                        MAStyle.ColorToken.background.opacity(0.92),
                        MAStyle.ColorToken.background.opacity(0.88)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
    }
}

public struct GlassPanel: ViewModifier {
    public func body(content: Content) -> some View {
        content
            .padding(MAStyle.Spacing.sm)
            .background(.ultraThinMaterial)
            .overlay(
                RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                    .stroke(MAStyle.ColorToken.border.opacity(0.6), lineWidth: MAStyle.Borders.thin)
            )
            .cornerRadius(MAStyle.Radius.md)
    }
}

public struct GradientStroke: ViewModifier {
    let colors: [Color]
    let lineWidth: CGFloat
    public init(colors: [Color] = [MAStyle.ColorToken.primary, MAStyle.ColorToken.info], lineWidth: CGFloat = 1.0) {
        self.colors = colors
        self.lineWidth = lineWidth
    }
    public func body(content: Content) -> some View {
        content
            .overlay(
                RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                    .stroke(
                        LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing),
                        lineWidth: lineWidth
                    )
            )
    }
}

// MARK: - Text / Section Styling
public struct SectionTitle: ViewModifier {
    public func body(content: Content) -> some View {
        if #available(macOS 13.0, *) {
            content
                .font(MAStyle.Typography.headline)
                .foregroundColor(MAStyle.ColorToken.muted)
                .textCase(.uppercase)
                .tracking(0.8)
        } else {
            content
                .font(MAStyle.Typography.headline)
                .foregroundColor(MAStyle.ColorToken.muted)
                .textCase(.uppercase)
        }
    }
}

// MARK: - Focus / Skeleton / Effects
public struct FocusRing: ViewModifier {
    let isFocused: Bool
    public func body(content: Content) -> some View {
        content
            .overlay(
                RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                    .stroke(
                        isFocused ? MAStyle.ColorToken.primary.opacity(0.5) : Color.clear,
                        lineWidth: 1.2
                    )
            )
    }
}

// macOS blur material wrapper (macOS 12+ safe).
public struct VisualEffectBlur: NSViewRepresentable {
    public let material: NSVisualEffectView.Material
    public let blendingMode: NSVisualEffectView.BlendingMode

    public init(material: NSVisualEffectView.Material = .hudWindow,
                blendingMode: NSVisualEffectView.BlendingMode = .withinWindow) {
        self.material = material
        self.blendingMode = blendingMode
    }

    public func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.state = .active
        view.material = material
        view.blendingMode = blendingMode
        view.isEmphasized = false
        return view
    }

    public func updateNSView(_ nsView: NSVisualEffectView, context: Context) {
        nsView.material = material
        nsView.blendingMode = blendingMode
    }
}

public struct SkeletonView: View {
    let height: CGFloat
    let cornerRadius: CGFloat
    @State private var phase: CGFloat = -1.0
    public init(height: CGFloat = 14, cornerRadius: CGFloat = MAStyle.Radius.sm) {
        self.height = height
        self.cornerRadius = cornerRadius
    }
    public var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius)
            .fill(
                LinearGradient(colors: [
                    MAStyle.ColorToken.panel.opacity(0.35),
                    MAStyle.ColorToken.panel.opacity(0.55),
                    MAStyle.ColorToken.panel.opacity(0.35)
                ], startPoint: .leading, endPoint: .trailing)
            )
            .frame(height: height)
            .mask(
                Rectangle()
                    .fill(
                        LinearGradient(
                            colors: [.clear, Color.white.opacity(0.6), .clear],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .offset(x: phase * 200)
            )
            .onAppear {
                withAnimation(.linear(duration: 1.2).repeatForever(autoreverses: false)) {
                    phase = 1.2
                }
            }
    }
}

// MARK: - Transitions / Motion
public extension View {
    /// Applies a subtle fade/slide when appearing.
    func maModalTransition() -> some View {
        transition(.move(edge: .top).combined(with: .opacity))
    }

    /// Hover lift for cards or buttons.
    func maHoverLift(enabled: Bool = true) -> some View {
        modifier(MAHoverLift(enabled: enabled))
    }
}

private struct MAHoverLift: ViewModifier {
    @State private var hovering = false
    var enabled: Bool = true
    func body(content: Content) -> some View {
        content
            .scaleEffect(hovering && enabled ? 1.01 : 1.0)
            .shadow(color: hovering && enabled ? Color.black.opacity(0.25) : Color.clear,
                    radius: hovering && enabled ? 12 : 0,
                    x: 0, y: hovering && enabled ? 6 : 0)
            .animation(.easeInOut(duration: 0.15), value: hovering)
            .onHover { hovering = enabled && $0 }
    }
}

public struct PulseEffect: ViewModifier {
    let isActive: Bool
    @State private var animate = false
    public func body(content: Content) -> some View {
        content
            .scaleEffect(animate ? 1.02 : 1.0)
            .opacity(animate ? 1.0 : 0.92)
            .onAppear {
                guard isActive, !MAStyle.reduceMotionEnabled else { return }
                withAnimation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true)) {
                    animate = true
                }
            }
    }
}

public struct SlideIn: ViewModifier {
    let from: Edge
    let distance: CGFloat
    let delay: Double
    @State private var offset: CGFloat = 0
    public func body(content: Content) -> some View {
        content
            .offset(x: from == .leading ? -offset : (from == .trailing ? offset : 0),
                    y: from == .top ? -offset : (from == .bottom ? offset : 0))
            .onAppear {
                guard !MAStyle.reduceMotionEnabled else { return }
                offset = distance
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8).delay(delay)) {
                    offset = 0
                }
            }
    }
}

// MARK: - Active Outline / State Helpers
public extension View {
    /// Applies a subtle active outline and fill for selected/processing states.
    func maActiveOutline(isActive: Bool,
                         cornerRadius: CGFloat = MAStyle.Radius.md,
                         fillOpacity: Double = 0.08,
                         strokeOpacity: Double = 0.35,
                         lineWidth: CGFloat = 1.2) -> some View {
        overlay(
            RoundedRectangle(cornerRadius: cornerRadius)
                .stroke(isActive ? MAStyle.ColorToken.primary.opacity(strokeOpacity) : Color.clear,
                        lineWidth: isActive ? lineWidth : 0)
        )
        .background(
            RoundedRectangle(cornerRadius: cornerRadius)
                .fill(isActive ? MAStyle.ColorToken.primary.opacity(fillOpacity) : Color.clear)
        )
    }
}

// MARK: - Hover Icon Button
public struct HoverIconButton: View {
    let systemName: String
    let action: () -> Void
    let size: CGFloat
    let weight: Font.Weight
    @State private var hovering = false

    public init(_ systemName: String,
                size: CGFloat = 12,
                weight: Font.Weight = .medium,
                action: @escaping () -> Void) {
        self.systemName = systemName
        self.action = action
        self.size = size
        self.weight = weight
    }

    public var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: size, weight: weight))
                .foregroundColor(MAStyle.ColorToken.muted)
                .opacity(hovering ? 1.0 : 0.0)
        }
        .buttonStyle(.plain)
        .onHover { hovering = $0 }
    }
}

// MARK: - Motion Effects
public struct FloatEffect: ViewModifier {
    let amplitude: CGFloat
    let duration: Double
    @State private var up = false
    public func body(content: Content) -> some View {
        content
            .offset(y: up ? -amplitude : amplitude)
            .onAppear {
                guard !MAStyle.reduceMotionEnabled else { return }
                withAnimation(.easeInOut(duration: duration).repeatForever(autoreverses: true)) {
                    up = true
                }
            }
    }
}

public struct FadeIn: ViewModifier {
    let delay: Double
    @State private var visible = false
    public func body(content: Content) -> some View {
        content
            .opacity(visible ? 1.0 : 0.0)
            .onAppear {
                guard !MAStyle.reduceMotionEnabled else { visible = true; return }
                withAnimation(.easeOut(duration: 0.25).delay(delay)) {
                    visible = true
                }
            }
    }
}

public struct ShakeEffect: GeometryEffect {
    var travel: CGFloat = 6
    var shakesPerUnit = 3
    public var animatableData: CGFloat
    public func effectValue(size: CGSize) -> ProjectionTransform {
        let translation = travel * sin(animatableData * .pi * CGFloat(shakesPerUnit))
        return ProjectionTransform(CGAffineTransform(translationX: translation, y: 0))
    }
}

extension View {
    // MARK: - Icons / Tags
    public func maIcon(_ systemName: String, size: CGFloat = 14, weight: Font.Weight = .regular, color: Color? = nil) -> some View {
        MAIcon(systemName, size: size, weight: weight, color: color)
    }

    public func maTag(_ text: String, icon: String? = nil, tone: MAStyle.Badge.Tone = .neutral) -> some View {
        MATag(text, icon: icon, tone: tone)
    }

    // MARK: - Layout / Background
    public func maStackSpacing(_ spacing: CGFloat = MAStyle.Spacing.sm) -> some View {
        modifier(MAStackSpacing(spacing: spacing))
    }

    public func maAppBackground() -> some View {
        modifier(AppBackground())
    }

    public func maGlass() -> some View {
        modifier(GlassPanel())
    }

    public func maGradientBorder(colors: [Color] = [MAStyle.ColorToken.primary, MAStyle.ColorToken.info], lineWidth: CGFloat = MAStyle.Borders.thin) -> some View {
        modifier(GradientStroke(colors: colors, lineWidth: lineWidth))
    }

    // MARK: - Text / Focus
    public func maSectionTitle() -> some View {
        modifier(SectionTitle())
    }

    public func maFocusRing(_ isFocused: Bool) -> some View {
        modifier(FocusRing(isFocused: isFocused))
    }

    public func maAnimated<Value: Equatable>(_ animation: Animation, value: Value) -> some View {
        self.animation(MAStyle.reduceMotionEnabled ? nil : animation, value: value)
    }

    // MARK: - Controls / Pickers
    public func maSegmentedStyle() -> some View {
        self
            .padding(.vertical, MAStyle.Spacing.xs)
            .padding(.horizontal, MAStyle.Spacing.sm)
            .background(MAStyle.ColorToken.panel.opacity(0.6))
            .overlay(
                RoundedRectangle(cornerRadius: MAStyle.Radius.sm)
                    .stroke(MAStyle.ColorToken.border, lineWidth: MAStyle.Borders.thin)
            )
            .cornerRadius(MAStyle.Radius.sm)
            .onHover { hovering in
                if MAStyle.reduceMotionEnabled { return }
                if hovering {
                    NSCursor.pointingHand.push()
                } else {
                    NSCursor.pop()
                }
            }
    }

    public func maPickerHover() -> some View {
        self
            .onHover { hovering in
                if MAStyle.reduceMotionEnabled { return }
                if hovering {
                    NSCursor.pointingHand.push()
                } else {
                    NSCursor.pop()
                }
            }
    }

    public func maToggleStyle() -> some View {
        self
            .toggleStyle(.switch)
            .tint(MAStyle.ColorToken.primary)
    }

    public func maSliderStyle() -> some View {
        self
            .tint(MAStyle.ColorToken.primary)
    }

    public func maFocusable(_ isFocused: Binding<Bool>, cornerRadius: CGFloat = MAStyle.Radius.md) -> some View {
        self
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(isFocused.wrappedValue ? MAStyle.ColorToken.primary.opacity(0.8) : Color.clear, lineWidth: isFocused.wrappedValue ? 2 : 0)
            )
    }

    public func maPickerFocus(_ isFocused: Binding<Bool>) -> some View {
        self
            .overlay(
                RoundedRectangle(cornerRadius: MAStyle.Radius.sm)
                    .stroke(isFocused.wrappedValue ? MAStyle.ColorToken.primary.opacity(0.8) : Color.clear, lineWidth: isFocused.wrappedValue ? 2 : 0)
            )
    }

    public func maPulse(isActive: Bool = true) -> some View {
        modifier(PulseEffect(isActive: isActive))
    }

    public func maSlideIn(from: Edge = .leading, distance: CGFloat = 24, delay: Double = 0) -> some View {
        modifier(SlideIn(from: from, distance: distance, delay: delay))
    }

    public func maFloat(amplitude: CGFloat = 6, duration: Double = 1.6) -> some View {
        modifier(FloatEffect(amplitude: amplitude, duration: duration))
    }

    public func maFadeIn(delay: Double = 0) -> some View {
        modifier(FadeIn(delay: delay))
    }

    public func maShake(animatableData: CGFloat, travel: CGFloat = 6, shakesPerUnit: Int = 3) -> some View {
        self.modifier(ShakeEffect(travel: travel, shakesPerUnit: shakesPerUnit, animatableData: animatableData))
    }
}
