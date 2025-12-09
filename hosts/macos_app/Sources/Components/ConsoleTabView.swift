import SwiftUI
import MAStyle

struct ChatContextOption: Identifiable, Equatable {
    let id: String
    let label: String
    let path: String?
}

struct ConsoleTabView: View {
    @Binding var prompt: String
    var messages: [String]
    var snippets: [String] = ["status", "help", "rerun last"]
    var onSend: () -> Void
    var onClear: () -> Void = {}
    var onSnippet: (String) -> Void = { _ in }
    var onStop: () -> Void = {}
    var promptFocus: FocusState<Bool>.Binding?
    var isThinking: Bool = false
    var contextOptions: [ChatContextOption] = []
    var selectedContext: Binding<String?> = .constant(nil)
    var contextLabel: String = "No context"

    var body: some View {
        HStack(alignment: .top, spacing: MAStyle.Spacing.md) {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
                HStack {
                    Text("Console / Chat")
                        .maText(.headline)
                    Spacer()
                    if isThinking {
                        HStack(spacing: MAStyle.Spacing.xs) {
                            ProgressView()
                                .scaleEffect(0.8)
                            Text("Thinking…")
                                .maText(.caption)
                                .foregroundStyle(MAStyle.ColorToken.muted)
                        }
                        .accessibilityLabel("Chat in progress")
                        Button("Stop") { onStop() }
                            .maButton(.ghost)
                            .accessibilityLabel("Stop chat")
                    }
                    Button("Clear") { onClear() }
                        .maButton(.ghost)
                        .accessibilityLabel("Clear console")
                }
                ConsoleView(messages: messages)
                    .frame(maxHeight: .infinity, alignment: .topLeading)
                Picker("Context", selection: selectedContext) {
                    ForEach(contextOptions) { option in
                        Text(option.label).tag(Optional.some(option.id))
                    }
                }
                .pickerStyle(.segmented)
                .accessibilityLabel("Chat context")
                Text("Using: \(contextLabel)")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                PromptView(text: $prompt, onSend: onSend, focus: promptFocus)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .onAppear {
                promptFocus?.wrappedValue = true
            }

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
        .overlay(
            Group {
                Button(action: onSend) { EmptyView() }
                    .keyboardShortcut(.return, modifiers: [.command])
                Button(action: onClear) { EmptyView() }
                    .keyboardShortcut("k", modifiers: [.command])
            }
            .opacity(0)
        )
    }
}
