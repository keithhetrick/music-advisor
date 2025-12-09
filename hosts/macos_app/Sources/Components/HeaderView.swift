import SwiftUI
import MAStyle

struct HeaderView: View {
    var hostStatus: String = "Live"
    var progress: Double = 0
    var showProgress: Bool = false
    var lastUpdated: Date? = nil
    var body: some View {
        HeaderBar(title: "Music Advisor",
                  subtitle: "SwiftUI shell; configure any local CLI and pipeline.") {
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
