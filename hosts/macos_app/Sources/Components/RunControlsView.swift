import SwiftUI
import MAStyle

struct RunControlsView: View {
    var isRunning: Bool
    var status: String
    var lastRunTime: Date?
    var lastDuration: TimeInterval?
    var onRun: () -> Void
    var onRunDefaults: () -> Void
    var onRunSmoke: () -> Void

    var body: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            Button(action: onRun) {
                if isRunning {
                    ProgressView().progressViewStyle(.circular)
                } else {
                    Text("Run CLI")
                }
            }
            .maButton(.primary)
            .disabled(isRunning)

            Button("Run defaults") {
                onRunDefaults()
            }
            .maButton(.secondary)
            .disabled(isRunning)

            Button("Run smoke") {
                onRunSmoke()
            }
            .maButton(.ghost)
            .disabled(isRunning)

            if !status.isEmpty {
                Text(status)
                    .maBadge(.info)
            }

            if let last = lastRunTime {
                let durationText = lastDuration.map { String(format: " (%.2fs)", $0) } ?? ""
                Text("Last run: \(last.formatted(date: .omitted, time: .standard))\(durationText)")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            Spacer()
        }
    }
}
