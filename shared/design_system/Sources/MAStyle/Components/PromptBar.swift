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

    private var canSend: Bool {
        !isThinking && !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private func sendIfPossible() {
        guard canSend else { return }
        onSend()
        refocus()
    }

    private func refocus() {
        // Keep focus for fast consecutive sends.
        DispatchQueue.main.async {
            if let focus = focus {
                focus.wrappedValue = true
            } else {
                internalFocus = true
            }
        }
    }

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
                .submitLabel(.send)
                .disabled(isThinking)
                .onSubmit {
                    sendIfPossible()
                }
                .onAppear {
                    refocus()
                }
                .onChange(of: isThinking) { thinking in
                    if !thinking {
                        refocus()
                    }
                }
            if let trailing { trailing }
            Button("Send") { sendIfPossible() }
                .maButton(.primary)
                .disabled(!canSend)
            Button("Clear") { onClear() }
                .maButton(.ghost)
                .disabled(text.isEmpty)
        }
        .padding(.vertical, MAStyle.Spacing.xs)
    }
}
