import SwiftUI
import AppKit
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
    var onDevSmoke: () -> Void = {}
    var promptFocus: FocusState<Bool>.Binding?
    var isThinking: Bool = false
    var contextOptions: [ChatContextOption] = []
    var selectedContext: Binding<String?> = .constant(nil)
    var contextLabel: String = "No context"
    var contextBadgeTitle: String = "No context"
    var contextBadgeSubtitle: String = ""
    var contextLastUpdated: Date? = nil
    var contextPath: String? = nil
    @State private var showSnippetsPopover: Bool = false
    @State private var snippetSearch: String = ""

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
                headerSection
                consoleSection
                contextPickerSection
                snippetSection
                contextBadge
                contextPreviewSection
                promptSection
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
                Button(action: onDevSmoke) { EmptyView() }
                    .keyboardShortcut("e", modifiers: [.command, .option]) // Cmd+Opt+E runs chat engine smoke (dev)
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

    // MARK: - Sections

    private var headerSection: some View {
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
    }

    private var consoleSection: some View {
        ConsoleView(messages: messages)
            .frame(maxHeight: .infinity, alignment: .topLeading)
            .padding(.bottom, MAStyle.Spacing.xs)
    }

    private var contextPickerSection: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
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
        }
    }

    @ViewBuilder
    private var snippetSection: some View {
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
    }

    private var promptSection: some View {
        PromptBar(
            text: $prompt,
            placeholder: "Type a message…",
            isThinking: isThinking,
            focus: promptFocus,
            onSend: onSend,
            onClear: onClear
        )
    }

    private var contextBadge: some View {
        ContextBadgeView(
            title: contextBadgeTitle,
            subtitle: contextBadgeSubtitle,
            lastUpdated: contextLastUpdated,
            path: contextPath,
            onOpen: contextPath.map { path in
                { NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)]) }
            }
        )
    }

    @ViewBuilder
    private var contextPreviewSection: some View {
        if let path = contextPath {
            ContextPreviewPanel(
                path: path,
                fullText: Self.contextFull(path: path)
            )
        } else if contextBadgeTitle == "No context" {
            Text("Pick or drop a .client.rich.txt so replies stay relevant to your song.")
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
                .padding(.top, -MAStyle.Spacing.xs)
        }
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

    // MARK: - Helpers
    private static func contextFull(path: String) -> String? {
        guard FileManager.default.fileExists(atPath: path) else { return nil }
        guard let data = try? String(contentsOfFile: path, encoding: .utf8) else { return nil }
        let trimmed = data.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty { return nil }
        return trimmed
    }
}

// MARK: - Context Preview Panel

private struct ContextPreviewPanel: View {
    let path: String
    let fullText: String?

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                Text("Context preview — \(URL(fileURLWithPath: path).lastPathComponent)")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            if let text = fullText {
                ScrollView {
                    Text(text)
                        .maText(.caption)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, MAStyle.Spacing.xs)
                }
                .frame(minHeight: 220, maxHeight: 520)
                .padding(MAStyle.Spacing.sm)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: MAStyle.Spacing.sm, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: MAStyle.Spacing.sm, style: .continuous)
                        .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                )
            } else {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    Text("Context preview unavailable for \(URL(fileURLWithPath: path).lastPathComponent).")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                    Text("Open the file to view its contents.")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
                .padding(MAStyle.Spacing.sm)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: MAStyle.Spacing.sm, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: MAStyle.Spacing.sm, style: .continuous)
                        .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                )
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, MAStyle.Spacing.xs)
    }
}
