import SwiftUI
import AppKit
import MAStyle

struct ConsoleView: View {
    var messages: [String]
    @StateObject private var scrollController = ScrollToBottomController()

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Console")
                .maText(.headline)
            ChatLogView(messages: messages,
                        scrollController: scrollController,
                        minHeight: 240,
                        maxHeight: 240,
                        onCopy: copy)
                .maCardInteractive()
        }
        .maCardInteractive()
        .textSelection(.enabled)
        .accessibilityLabel("Console output")
    }

    private func copy(_ text: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
    }
}
