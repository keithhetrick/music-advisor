import SwiftUI

public enum MAAlertTone {
    case info, success, warning, danger
    var color: Color {
        switch self {
        case .info: return MAStyle.ColorToken.info
        case .success: return MAStyle.ColorToken.success
        case .warning: return MAStyle.ColorToken.warning
        case .danger: return MAStyle.ColorToken.danger
        }
    }
    var icon: String {
        switch self {
        case .info: return "info.circle"
        case .success: return "checkmark.circle"
        case .warning: return "exclamationmark.triangle"
        case .danger: return "xmark.octagon"
        }
    }
}

public struct MAAlertBanner: View {
    let title: String
    let message: String?
    let tone: MAAlertTone
    let dismissible: Bool
    let onDismiss: (() -> Void)?

    public init(title: String, message: String? = nil, tone: MAAlertTone = .info, dismissible: Bool = false, onDismiss: (() -> Void)? = nil) {
        self.title = title
        self.message = message
        self.tone = tone
        self.dismissible = dismissible
        self.onDismiss = onDismiss
    }

    public var body: some View {
        HStack(alignment: .top, spacing: MAStyle.Spacing.sm) {
            MAIcon(tone.icon, size: 14, weight: .semibold, color: tone.color)
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text(title)
                    .font(MAStyle.Typography.headline)
                    .foregroundColor(tone.color)
                if let message {
                    Text(message)
                        .font(MAStyle.Typography.body)
                        .foregroundColor(MAStyle.ColorToken.muted)
                }
            }
            Spacer()
            if dismissible {
                Button {
                    onDismiss?()
                } label: {
                    MAIcon("xmark", size: 11, weight: .semibold, color: MAStyle.ColorToken.muted)
                }
                .buttonStyle(MAStyle.InteractiveButtonStyle(variant: .ghost))
            }
        }
        .padding(MAStyle.Spacing.md)
        .background(tone.color.opacity(0.08))
        .overlay(
            RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                .stroke(tone.color.opacity(0.35), lineWidth: MAStyle.Borders.thin)
        )
        .cornerRadius(MAStyle.Radius.md)
    }
}

public struct MAToastBanner: View {
    let title: String
    let tone: MAAlertTone
    public init(title: String, tone: MAAlertTone = .info) {
        self.title = title
        self.tone = tone
    }
    public var body: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            MAIcon(tone.icon, size: 12, weight: .semibold, color: tone.color)
            Text(title)
                .font(MAStyle.Typography.body)
                .foregroundColor(MAStyle.ColorToken.muted)
            Spacer()
        }
        .padding(MAStyle.Spacing.sm)
        .background(MAStyle.ColorToken.panel.opacity(0.9))
        .overlay(RoundedRectangle(cornerRadius: MAStyle.Radius.md).stroke(tone.color.opacity(0.25), lineWidth: MAStyle.Borders.thin))
        .cornerRadius(MAStyle.Radius.md)
        .shadow(color: Color.black.opacity(0.2), radius: 8, x: 0, y: 4)
    }
}
