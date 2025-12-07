import SwiftUI
import MAStyle

struct HeaderView: View {
    var hostStatus: String = "Live"
    var progress: Double = 0
    var showProgress: Bool = false
    var lastUpdated: Date? = nil
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text("Music Advisor")
                    .maText(.headline)
                Text("SwiftUI shell; configure any local CLI and pipeline.")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                if let lastUpdated {
                    Text("Updated: \(lastUpdated.formatted(date: .omitted, time: .standard))")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
            }
            Spacer()
            HStack(spacing: MAStyle.Spacing.xs) {
                Text(hostStatus)
                    .maBadge(.success)
                if showProgress {
                    ProgressView(value: progress)
                        .maProgressStyle()
                        .frame(width: 80)
                }
            }
        }
        .maCard(padding: MAStyle.Spacing.sm)
    }
}
