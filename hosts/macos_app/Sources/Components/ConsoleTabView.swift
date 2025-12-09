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
    var onPickContext: () -> Void = {}
    var promptFocus: FocusState<Bool>.Binding?
    var isThinking: Bool = false
    var contextOptions: [ChatContextOption] = []
    var selectedContext: Binding<String?> = .constant(nil)
    var contextLabel: String = "No context"
    @State private var showSnippetsPopover: Bool = false
    @State private var snippetSearch: String = ""

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
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
                HStack(spacing: MAStyle.Spacing.xs) {
                    Text("Using: \(contextLabel)")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                    Spacer()
                    Button("Pick context…") { onPickContext() }
                        .maButton(.ghost)
                        .accessibilityLabel("Pick a context file for chat")
                }
                // Quick inline chips for top snippets (non-blocking) with fixed FAB anchor
                if !snippets.isEmpty {
                    ChipRow(
                        items: quickSnippetItems,
                        style: .solid,
                        trailingSpacing: 52,
                        trailingContent: AnyView(
                            FABPopover(
                                icon: "text.badge.plus",
                                items: snippetItems,
                                onSelect: { item in
                                    onSnippet(item.value)
                                }
                            )
                        )
                    ) { item in
                        onSnippet(item.value)
                    }
                }
                PromptBar(
                    text: $prompt,
                    placeholder: "Type a message…",
                    isThinking: isThinking,
                    focus: promptFocus,
                    onSend: onSend,
                    onClear: onClear
                )
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .onAppear {
                promptFocus?.wrappedValue = true
            }
        }
        .overlay(
            Group {
                Button(action: onSend) { EmptyView() }
                    .keyboardShortcut(.return, modifiers: [.command])
                Button(action: onClear) { EmptyView() }
                    .keyboardShortcut("k", modifiers: [.command])
                Button(action: { withAnimation { showSnippetsPopover.toggle() } }) { EmptyView() }
                    .keyboardShortcut("s", modifiers: [.command, .option]) // Cmd+Opt+S toggles snippets drawer
            }
            .opacity(0)
        )
    }

    private var quickSnippets: [String] {
        Array(snippets.prefix(4))
    }

    private var quickSnippetItems: [SnippetItem] {
        quickSnippets.map { SnippetItem(value: $0) }
    }

    private var snippetItems: [SnippetItem] {
        snippets.map { SnippetItem(value: $0) }
    }

    private var filteredSnippets: [String] {
        let trimmed = snippetSearch.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return snippets }
        return snippets.filter { $0.localizedCaseInsensitiveContains(trimmed) }
    }

    struct SnippetItem: Identifiable, Hashable, CustomStringConvertible {
        let id = UUID()
        let value: String
        var description: String { value }
    }
}
