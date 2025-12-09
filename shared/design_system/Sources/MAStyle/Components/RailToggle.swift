import SwiftUI

// MARK: - Rail toggle control
public struct RailToggle: View {
    public enum State {
        case shown
        case hidden
    }

    let state: State
    let toggle: () -> Void
    let compact: Bool
    let slideFromLeft: Bool
    @SwiftUI.State private var hovering = false

    public init(state: State, compact: Bool = false, slideFromLeft: Bool = false, toggle: @escaping () -> Void) {
        self.state = state
        self.toggle = toggle
        self.compact = compact
        self.slideFromLeft = slideFromLeft
    }

    @ViewBuilder
    public var body: some View {
        if compact {
            Button(action: toggle) { label }
                .buttonStyle(.plain)
                .padding(.horizontal, 8)
                .padding(.vertical, 6)
                .background(
                    Capsule()
                        .fill(MAStyle.ColorToken.panel.opacity(hovering ? 0.30 : 0.08))
                )
                .overlay(
                    Capsule()
                        .stroke(MAStyle.ColorToken.border.opacity(hovering ? 0.34 : 0.12), lineWidth: MAStyle.Borders.thin)
                )
                .opacity(hovering ? 1.0 : 0.16)        // very faint idle; bright on hover
                .offset(x: hovering ? 0 : (slideFromLeft ? -10 : 10)) // subtle tuck until hover
                .contentShape(Capsule())
                .help(state == .shown ? "Hide navigation" : "Show navigation")
                .onHover { isHovering in
                    withAnimation(.easeOut(duration: 0.42)) {
                        hovering = isHovering
                    }
                }
        } else {
            Button(action: toggle) { label }
                .buttonStyle(MAStyle.InteractiveButtonStyle(variant: .ghost))
        }
    }

    private var label: some View {
        let icon = state == .shown ? "sidebar.trailing" : "sidebar.leading"
        if compact {
            return AnyView(
                Image(systemName: icon)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(MAStyle.ColorToken.muted)
            )
        } else {
            let text = state == .shown ? "Hide rail" : "Show rail"
            return AnyView(Label(text, systemImage: icon))
        }
    }
}
