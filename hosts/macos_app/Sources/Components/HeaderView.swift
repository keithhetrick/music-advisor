import SwiftUI
import MAStyle

struct HeaderView: View {
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text("Music Advisor")
                    .maText(.headline)
                Text("SwiftUI shell; configure any local CLI and pipeline.")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            Spacer()
            Text("Live")
                .maBadge(.success)
        }
        .maCard(padding: MAStyle.Spacing.sm)
    }
}
