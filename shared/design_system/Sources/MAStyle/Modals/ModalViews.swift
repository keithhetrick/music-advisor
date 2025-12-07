import SwiftUI

public enum MAModalStyle {
    case dialog
    case sheet
    case toast
    case popup
}

public struct MAModalAction: Identifiable {
    public let id = UUID()
    public let title: String
    public let role: ButtonRole?
    public let action: () -> Void

    public init(_ title: String, role: ButtonRole? = nil, action: @escaping () -> Void) {
        self.title = title
        self.role = role
        self.action = action
    }
}

public struct MAModal<Content: View>: View {
    @Binding var isPresented: Bool
    let style: MAModalStyle
    let title: String?
    let actions: [MAModalAction]
    let content: Content

    public init(isPresented: Binding<Bool>,
                style: MAModalStyle = .dialog,
                title: String? = nil,
                actions: [MAModalAction] = [],
                @ViewBuilder content: () -> Content) {
        self._isPresented = isPresented
        self.style = style
        self.title = title
        self.actions = actions
        self.content = content()
    }

    public var body: some View {
        ZStack {
            if isPresented {
                backdrop
                modalBody
                    .transition(transition)
                    .zIndex(1)
            }
        }
        .animation(.spring(response: 0.28, dampingFraction: 0.82), value: isPresented)
    }

    private var backdrop: some View {
        Color.black.opacity(style == .toast ? 0.0 : 0.35)
            .ignoresSafeArea()
            .onTapGesture {
                isPresented = false
            }
    }

    @ViewBuilder
    private var modalBody: some View {
        switch style {
        case .dialog:
            dialogBody
                .frame(maxWidth: 420)
                .maCard(padding: MAStyle.Spacing.md)
                .maGradientBorder()
                .shadow(color: .black.opacity(0.45), radius: 18, x: 0, y: 12)
                .scaleEffect(isPresented ? 1.0 : 0.96)
                .opacity(isPresented ? 1.0 : 0.0)
        case .sheet:
            VStack {
                Spacer()
                dialogBody
                    .frame(maxWidth: 520)
                    .maCard(padding: MAStyle.Spacing.md)
                    .maGradientBorder()
                    .shadow(color: .black.opacity(0.30), radius: 12, x: 0, y: 8)
                    .offset(y: isPresented ? 0 : 40)
                    .opacity(isPresented ? 1.0 : 0.0)
            }
            .padding(.bottom, MAStyle.Spacing.lg)
        case .toast:
            VStack {
                Spacer()
                HStack {
                    dialogBody
                        .maCard(padding: MAStyle.Spacing.md)
                        .maGradientBorder()
                        .shadow(color: .black.opacity(0.25), radius: 10, x: 0, y: 6)
                        .offset(y: isPresented ? 0 : 20)
                        .opacity(isPresented ? 1.0 : 0.0)
                }
                .padding(.bottom, MAStyle.Spacing.lg)
            }
            .padding(.horizontal, MAStyle.Spacing.lg)
        case .popup:
            dialogBody
                .frame(maxWidth: 360)
                .maCard(padding: MAStyle.Spacing.md)
                .maGradientBorder()
                .shadow(color: .black.opacity(0.35), radius: 14, x: 0, y: 10)
                .scaleEffect(isPresented ? 1.02 : 0.94)
                .opacity(isPresented ? 1.0 : 0.0)
                .offset(y: isPresented ? 0 : -10)
        }
    }

    private var dialogBody: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            HStack {
                if let title {
                    Text(title)
                        .font(MAStyle.Typography.headline)
                        .foregroundColor(MAStyle.ColorToken.muted)
                }
                Spacer()
                Button {
                    isPresented = false
                } label: {
                    MAIcon("xmark", size: 12, weight: .semibold, color: MAStyle.ColorToken.muted)
                }
                .buttonStyle(MAStyle.InteractiveButtonStyle(variant: .ghost))
            }
            content
                .font(MAStyle.Typography.body)
                .foregroundColor(MAStyle.ColorToken.muted)

            if !actions.isEmpty {
                HStack(spacing: MAStyle.Spacing.sm) {
                    ForEach(actions) { action in
                        Button(action.title) {
                            action.action()
                            isPresented = false
                        }
                        .buttonStyle(MAStyle.InteractiveButtonStyle(
                            variant: action.role == .destructive ? .secondary : .primary
                        ))
                    }
                    Spacer()
                }
            }
        }
    }

    private var transition: AnyTransition {
        switch style {
        case .dialog, .popup:
            return .scale.combined(with: .opacity)
        case .sheet:
            return .move(edge: .bottom).combined(with: .opacity)
        case .toast:
            return .move(edge: .bottom).combined(with: .opacity)
        }
    }
}
