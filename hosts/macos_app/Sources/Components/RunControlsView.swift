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
    var onRevealLastSidecar: (() -> Void)? = nil
    var onToggleTheme: (() -> Void)? = nil

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
            .keyboardShortcut(.return, modifiers: [.command])
            .accessibilityLabel("Run")

            Button("Run defaults") {
                onRunDefaults()
            }
            .maButton(.secondary)
            .disabled(isRunning)
            .keyboardShortcut(.return, modifiers: [.command, .shift])
            .accessibilityLabel("Run defaults")

            Button("Run smoke") {
                onRunSmoke()
            }
            .maButton(.ghost)
            .disabled(isRunning)
            .keyboardShortcut(.return, modifiers: [.command, .option])
            .accessibilityLabel("Run smoke test")

            if let onRevealLastSidecar {
                Button("Reveal last") { onRevealLastSidecar() }
                    .maButton(.ghost)
                    .keyboardShortcut("r", modifiers: [.command])
                    .accessibilityLabel("Reveal last sidecar")
            }
            if let onToggleTheme {
                Button("Theme") { onToggleTheme() }
                    .maButton(.ghost)
                    .keyboardShortcut("t", modifiers: [.command])
                    .accessibilityLabel("Toggle theme")
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
            Spacer()
        }
    }
}
