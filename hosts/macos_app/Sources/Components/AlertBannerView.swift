import SwiftUI
import MAStyle

struct AlertBannerView: View {
    var alert: AlertState
    var onDismiss: () -> Void

    private var color: Color {
        switch alert.level {
        case .info: return MAStyle.ColorToken.info
        case .warning: return MAStyle.ColorToken.warning
        case .error: return MAStyle.ColorToken.danger
        }
    }

    var body: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            Circle()
                .fill(color)
                .frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text(alert.title)
                    .maText(.body)
                Text(alert.message)
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            Spacer()
            Button {
                onDismiss()
            } label: {
                Image(systemName: "xmark")
            }
            .maButton(.ghost)
        }
        .padding(MAStyle.Spacing.sm)
        .background(MAStyle.ColorToken.panel.opacity(0.9))
        .overlay(
            RoundedRectangle(cornerRadius: MAStyle.Radius.sm)
                .stroke(color.opacity(0.6), lineWidth: 1)
        )
        .cornerRadius(MAStyle.Radius.sm)
        .shadow(color: color.opacity(0.2), radius: 8, x: 0, y: 4)
    }
}
