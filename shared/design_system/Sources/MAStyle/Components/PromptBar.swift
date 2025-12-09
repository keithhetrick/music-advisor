import SwiftUI

// MARK: - PromptBar
/// Reusable prompt bar with send/clear actions and optional trailing controls.
public struct PromptBar: View {
    @Binding var text: String
    let placeholder: String
    let onSend: () -> Void
    let onClear: () -> Void
    let isThinking: Bool
    let trailing: AnyView?
    let focus: FocusState<Bool>.Binding?
    @FocusState private var internalFocus: Bool

    public init(text: Binding<String>,
                placeholder: String = "Type a message…",
                isThinking: Bool = false,
                focus: FocusState<Bool>.Binding? = nil,
                trailing: AnyView? = nil,
                onSend: @escaping () -> Void,
                onClear: @escaping () -> Void) {
        self._text = text
        self.placeholder = placeholder
        self.onSend = onSend
        self.onClear = onClear
        self.isThinking = isThinking
        self.trailing = trailing
        self.focus = focus
    }

    public var body: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            TextField(placeholder, text: $text)
                .textFieldStyle(.roundedBorder)
                .focused(focus ?? $internalFocus)
                .disabled(isThinking)
            if let trailing { trailing }
            Button("Send") { onSend() }
                .maButton(.primary)
                .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isThinking)
            Button("Clear") { onClear() }
                .maButton(.ghost)
                .disabled(text.isEmpty)
        }
    }
}
