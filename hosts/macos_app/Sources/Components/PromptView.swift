import SwiftUI
import MAStyle

struct PromptView: View {
    @Binding var text: String
    var onSend: () -> Void
    var focus: FocusState<Bool>.Binding?

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text("Prompt")
                .maText(.caption)
            HStack {
                textField
                Button("Send") {
                    onSend()
                }
                .maButton(.primary)
            }
        }
        .maCardInteractive()
    }

    @ViewBuilder
    private var textField: some View {
        if let focus {
            TextField("Type a message…", text: $text)
                .maInput()
                .focused(focus)
                .disabled(false)
                .focusable(true)
                .onSubmit { onSend() }
        } else {
            TextField("Type a message…", text: $text)
                .maInput()
                .disabled(false)
                .focusable(true)
                .onSubmit { onSend() }
        }
    }
}
