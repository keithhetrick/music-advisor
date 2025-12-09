import SwiftUI
import MAStyle

struct ConsoleTabPlaceholder: View {
    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Console / Chat coming soon")
                .maText(.headline)
            Text("Use this space for live logs, chat, and quick prompts.")
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
        .maCard()
    }
}
