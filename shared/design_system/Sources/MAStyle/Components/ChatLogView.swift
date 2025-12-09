import SwiftUI

// MARK: - ChatLogView
public struct ChatLogView: View {
    let messages: [String]
    @ObservedObject var scrollController: ScrollToBottomController
    let onCopy: (String) -> Void

    public init(messages: [String],
                scrollController: ScrollToBottomController,
                onCopy: @escaping (String) -> Void) {
        self.messages = messages
        self._scrollController = ObservedObject(initialValue: scrollController)
        self.onCopy = onCopy
    }

    public var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    ForEach(messages.indices, id: \.self) { idx in
                        CopyableMonoRow(messages[idx]) { onCopy(messages[idx]) }
                            .id(idx)
                    }
                    Color.clear
                        .frame(height: 1)
                        .id("chat-bottom")
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .gesture(DragGesture().onChanged { _ in
                    scrollController.didScrollAway()
                })
            }
            .onAppear {
                proxy.scrollTo("chat-bottom", anchor: .bottom)
                scrollController.didScrollToBottom()
            }
            .onChange(of: messages.count) { _ in
                withAnimation {
                    proxy.scrollTo("chat-bottom", anchor: .bottom)
                }
                scrollController.didScrollToBottom()
            }
            .onChange(of: scrollController.showJump) { show in
                if !show {
                    withAnimation {
                        proxy.scrollTo("chat-bottom", anchor: .bottom)
                    }
                }
            }
            .overlay(alignment: .bottomTrailing) {
                if scrollController.showJump && !messages.isEmpty {
                    JumpToBottomButton {
                        scrollController.jump()
                    }
                }
            }
        }
    }
}
