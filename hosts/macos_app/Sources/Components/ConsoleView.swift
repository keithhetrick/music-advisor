import SwiftUI
import MAStyle

struct ConsoleView: View {
    var messages: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Console")
                .maText(.headline)
            ScrollView {
                LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    ForEach(messages.indices, id: \.self) { idx in
                        Text(messages[idx])
                            .font(MAStyle.Typography.bodyMono)
                            .foregroundColor(MAStyle.ColorToken.muted)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(minHeight: 220)
            .maCardInteractive()
        }
        .maCardInteractive()
        .textSelection(.enabled)
    }
}
