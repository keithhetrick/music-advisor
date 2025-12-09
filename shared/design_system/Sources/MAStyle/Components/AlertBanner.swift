import SwiftUI

// MARK: - AlertBanner
/// Lightweight, reusable alert/toast banner for drop-in use across apps.
public struct AlertBanner: View {
    public enum Tone { case info, success, warning, error }
    public let title: String
    public let message: String?
    public let tone: Tone
    public let onClose: (() -> Void)?
    public let presentAsToast: Bool
    /// Optional auto-dismiss duration in seconds. If `nil`, the banner stays until closed.
    public let autoDismissSeconds: Double?

    @State private var progress: CGFloat = 1.0
    @State private var isVisible: Bool = true
    @State private var slideOffset: CGFloat = 0
    @State private var scaleX: CGFloat = 1.0

    public init(title: String,
                message: String? = nil,
                tone: Tone = .info,
                presentAsToast: Bool = false,
                autoDismissSeconds: Double? = nil,
                onClose: (() -> Void)? = nil) {
        self.title = title
        self.message = message
        self.tone = tone
        self.presentAsToast = presentAsToast
        self.autoDismissSeconds = autoDismissSeconds
        self.onClose = onClose
    }

    public var body: some View {
        VStack(spacing: MAStyle.Spacing.sm) {
            HStack(alignment: .top, spacing: MAStyle.Spacing.sm) {
                Image(systemName: icon)
                    .foregroundStyle(color)
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    Text(title)
                        .font(MAStyle.Typography.headline)
                        .foregroundStyle(color)
                    if let message, !message.isEmpty {
                        Text(message)
                            .font(MAStyle.Typography.body)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                    }
                }
                Spacer()
                if onClose != nil {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(MAStyle.ColorToken.muted)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Close")
                }
            }

            if effectiveAutoDismiss != nil {
                ToastProgressBar(progress: progress, color: color)
                    .animation(.linear(duration: effectiveAutoDismiss ?? 0), value: progress)
            }
        }
        .padding(MAStyle.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                .fill(MAStyle.ColorToken.panel.opacity(presentAsToast ? 0.94 : 1.0))
                .overlay(
                    RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                        .stroke(color.opacity(0.35), lineWidth: MAStyle.Borders.thin)
                )
        )
        .shadow(color: .black.opacity(0.15), radius: 8, x: 0, y: 4)
        .scaleEffect(x: scaleX, y: 1, anchor: .leading)
        .offset(x: slideOffset)
        .opacity(isVisible ? 1 : 0)
        .onAppear {
            slideOffset = 0
            scaleX = 1
            isVisible = true
            startAutoDismissIfNeeded()
        }
    }

    private var color: Color {
        switch tone {
        case .info: return MAStyle.ColorToken.info
        case .success: return MAStyle.ColorToken.success
        case .warning: return MAStyle.ColorToken.warning
        case .error: return MAStyle.ColorToken.danger
        }
    }

    private var icon: String {
        switch tone {
        case .info: return "info.circle"
        case .success: return "checkmark.seal"
        case .warning: return "exclamationmark.triangle"
        case .error: return "xmark.octagon"
        }
    }

    private var effectiveAutoDismiss: Double? {
        if let autoDismissSeconds { return autoDismissSeconds }
        return presentAsToast ? MAStyle.ToastDefaults.autoDismissSeconds : nil
    }

    private func startAutoDismissIfNeeded() {
        guard let seconds = effectiveAutoDismiss else { return }
        progress = 1.0
        withAnimation(.linear(duration: seconds)) {
            progress = 0.0
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + seconds) {
            dismiss()
        }
    }

    private func dismiss() {
        withAnimation(.spring(response: 0.5, dampingFraction: 0.85)) {
            scaleX = 0.82
            slideOffset = -32
            isVisible = false
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.32) {
            onClose?()
        }
    }
}
