import SwiftUI

public struct MAFocusableTableRow<Content: View>: View {
    let index: Int
    let isSelected: Bool
    let isDisabled: Bool
    let badgeCount: Int?
    let actionTitle: String?
    let action: (() -> Void)?
    let content: Content
    @State private var isFocused: Bool = false

    public init(index: Int,
                isSelected: Bool = false,
                isDisabled: Bool = false,
                badgeCount: Int? = nil,
                actionTitle: String? = nil,
                action: (() -> Void)? = nil,
                @ViewBuilder content: () -> Content) {
        self.index = index
        self.isSelected = isSelected
        self.isDisabled = isDisabled
        self.badgeCount = badgeCount
        self.actionTitle = actionTitle
        self.action = action
        self.content = content()
    }

    public var body: some View {
        MATableRow(index: index,
                   isSelected: isSelected,
                   isDisabled: isDisabled,
                   isFocused: isFocused,
                   badgeCount: badgeCount,
                   actionTitle: actionTitle,
                   action: action) {
            content
        }
        .background(
            FocusableWrapper(isFocused: $isFocused)
        )
    }

    private struct FocusableWrapper: NSViewRepresentable {
        @Binding var isFocused: Bool
        func makeNSView(context: Context) -> FocusableHostingView {
            let view = FocusableHostingView()
            view.onFocusChange = { focused in
                DispatchQueue.main.async {
                    self.isFocused = focused
                }
            }
            return view
        }
        func updateNSView(_ nsView: FocusableHostingView, context: Context) {}
    }

    private final class FocusableHostingView: NSView {
        var onFocusChange: ((Bool) -> Void)?
        override var acceptsFirstResponder: Bool { true }
        override func becomeFirstResponder() -> Bool {
            onFocusChange?(true)
            return true
        }
        override func resignFirstResponder() -> Bool {
            onFocusChange?(false)
            return true
        }
        override func viewDidMoveToWindow() {
            super.viewDidMoveToWindow()
            window?.makeFirstResponder(self)
        }
    }
}
