import SwiftUI
import MAStyle

struct ConsoleTabView: View {
    @Binding var prompt: String
    var messages: [String]
    var snippets: [String] = ["status", "help", "rerun last"]
    var onSend: () -> Void
    var onClear: () -> Void = {}
    var onSnippet: (String) -> Void = { _ in }
    var promptFocus: FocusState<Bool>.Binding?

    var body: some View {
        HStack(alignment: .top, spacing: MAStyle.Spacing.md) {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
                HStack {
                    Text("Console / Chat")
                        .maText(.headline)
                    Spacer()
                    Button("Clear") { onClear() }
                        .maButton(.ghost)
                        .accessibilityLabel("Clear console")
                }
                ConsoleView(messages: messages)
                    .frame(maxHeight: .infinity, alignment: .topLeading)
                PromptView(text: $prompt, onSend: onSend, focus: promptFocus)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                Text("Snippets")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                ForEach(snippets, id: \.self) { snippet in
                    Button(snippet) { onSnippet(snippet) }
                        .maButton(.ghost)
                        .accessibilityLabel("Insert snippet \(snippet)")
                }
                Spacer()
            }
            .frame(width: 180, alignment: .topLeading)
            .maCard()
            .maGlass()
        }
    }
}
