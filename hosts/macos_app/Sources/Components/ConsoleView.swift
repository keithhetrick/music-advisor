import SwiftUI
import AppKit
import MAStyle

struct ConsoleView: View {
    var messages: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Console")
                .maText(.headline)
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                        ForEach(messages.indices, id: \.self) { idx in
                            CopyableMonoRow(messages[idx]) { copy(messages[idx]) }
                        }
                        Color.clear
                            .frame(height: 1)
                            .id("console-bottom")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .onAppear {
                    proxy.scrollTo("console-bottom", anchor: .bottom)
                }
                .onChange(of: messages.count) { _ in
                    withAnimation {
                        proxy.scrollTo("console-bottom", anchor: .bottom)
                    }
                }
            }
            .frame(minHeight: 220, maxHeight: 220)
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
