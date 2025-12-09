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

    public init(title: String,
                message: String? = nil,
                tone: Tone = .info,
                presentAsToast: Bool = false,
                onClose: (() -> Void)? = nil) {
        self.title = title
        self.message = message
        self.tone = tone
        self.presentAsToast = presentAsToast
        self.onClose = onClose
    }

    public var body: some View {
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
            if let onClose {
                Button {
                    onClose()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Close")
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
}
