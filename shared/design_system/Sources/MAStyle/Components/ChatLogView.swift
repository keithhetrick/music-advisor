import SwiftUI

// MARK: - ChatLogView
public struct ChatLogView: View {
    let messages: [String]
    @ObservedObject var scrollController: ScrollToBottomController
    let onCopy: (String) -> Void

    private let minHeight: CGFloat
    private let maxHeight: CGFloat

    public init(messages: [String],
                scrollController: ScrollToBottomController,
                minHeight: CGFloat = 180,
                maxHeight: CGFloat = 240,
                onCopy: @escaping (String) -> Void) {
        self.messages = messages
        self._scrollController = ObservedObject(initialValue: scrollController)
        self.onCopy = onCopy
        self.minHeight = minHeight
        self.maxHeight = maxHeight
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
            .accessibilityLabel("Chat messages")
            .accessibilityElement(children: .contain)
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
            .frame(minHeight: minHeight, maxHeight: maxHeight)
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
