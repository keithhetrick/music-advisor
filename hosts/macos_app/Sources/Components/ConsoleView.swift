import SwiftUI
import MAStyle

struct ConsoleView: View {
    var messages: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Console")
                .maText(.headline)
            ScrollView {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    ForEach(messages.indices, id: \.self) { idx in
                        Text(messages[idx])
                            .font(.system(.body, design: .monospaced))
                            .foregroundColor(.primary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(minHeight: 220)
            .overlay(RoundedRectangle(cornerRadius: MAStyle.Radius.md).stroke(MAStyle.ColorToken.border))
        }
        .maCard()
    }
}
