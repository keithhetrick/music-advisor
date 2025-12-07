import SwiftUI
import MAStyle

struct PromptView: View {
    @Binding var text: String
    var onSend: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text("Prompt")
                .maText(.caption)
            HStack {
                TextField("Type a message…", text: $text)
                    .maInput()
                    .onSubmit { onSend() }
                Button("Send") {
                    onSend()
                }
                .maButton(.primary)
            }
        }
        .maCardInteractive()
    }
}
