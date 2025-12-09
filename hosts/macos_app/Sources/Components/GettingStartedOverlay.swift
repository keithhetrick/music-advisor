import SwiftUI
import MAStyle

struct GettingStartedOverlay: View {
    var onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            HStack {
                Text("Getting Started")
                    .maText(.headline)
                Spacer()
                Button("Got it") { onDismiss() }
                    .maButton(.primary)
            }
            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                step(title: "1. Drop or pick audio", detail: "Use the drop zone or “Pick audio” to enqueue files.")
                step(title: "2. Configure command", detail: "Adjust command, working directory, and env as needed.")
                step(title: "3. Run fast", detail: "Use Run (⌘⏎), defaults (⇧⌘⏎), or smoke (⌥⌘⏎).")
                step(title: "4. Review history", detail: "History tab shows saved sidecars with previews.")
                step(title: "5. Console", detail: "Console tab for messages; snippets prefill the prompt.")
            }
            Text("Tips: Use ⌘F to focus history search, ⌘L for console prompt, ⌘T for theme, ⌘R to reveal last sidecar.")
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
        .padding(MAStyle.Spacing.lg)
        .maCard()
        .maGlass()
    }

    private func step(title: String, detail: String) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title).maText(.body)
            Text(detail)
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
    }
}
