import SwiftUI
import MAStyle

struct RunControlsView: View {
    var isRunning: Bool
    var status: String
    var lastRunTime: Date?
    var lastDuration: TimeInterval?
    var canRun: Bool = true
    var disabledReason: String? = nil
    var warnings: [String] = []
    var onRun: () -> Void
    var onRunDefaults: () -> Void
    var onRunSmoke: () -> Void
    var onRevealLastSidecar: (() -> Void)? = nil

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
            .maFocusRing(true)
            .disabled(isRunning || !canRun)
            .keyboardShortcut(.return, modifiers: [.command])
            .accessibilityLabel("Run")

            Button("Run defaults", action: onRunDefaults)
                .maButton(.secondary)
                .maFocusRing(true)
            .disabled(isRunning || !canRun)
            .keyboardShortcut(.return, modifiers: [.command, .shift])
            .accessibilityLabel("Run defaults")

            Button("Run smoke", action: onRunSmoke)
                .maButton(.ghost)
                .maFocusRing(true)
            .disabled(isRunning)
            .keyboardShortcut(.return, modifiers: [.command, .option])
            .accessibilityLabel("Run smoke test")

            if let onRevealLastSidecar {
                Button("Reveal last", action: onRevealLastSidecar)
                    .maButton(.ghost)
                    .maFocusRing(true)
                    .keyboardShortcut("r", modifiers: [.command])
                    .accessibilityLabel("Reveal last sidecar")
            }

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
            if let disabledReason, !disabledReason.isEmpty, !canRun {
                Text(disabledReason)
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.danger)
            }
            ForEach(warnings, id: \.self) { warning in
                Text(warning)
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.warning)
            }
            Spacer()
        }
    }
}
