import SwiftUI
import MAStyle

struct RunHeaderView: View {
    var hostStatus: String
    var progress: Double
    var showProgress: Bool
    var onToggleTheme: () -> Void
    var canRun: Bool
    var disabledReason: String?

    var body: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            Text("Run")
                .maText(.headline)
            Spacer()
            Text(hostStatus)
                .maBadge(.info)
            if showProgress {
                ProgressView(value: progress)
                    .maProgressStyle()
                    .frame(width: 120)
            }
            if !canRun {
                Text(disabledReason ?? "Not ready")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.danger)
            }
        }
        .maCard(padding: MAStyle.Spacing.xs)
    }
}
