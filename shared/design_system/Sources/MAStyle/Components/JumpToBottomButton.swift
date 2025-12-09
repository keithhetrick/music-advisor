import SwiftUI

// MARK: - Jump-to-bottom control (reusable)
public struct JumpToBottomButton: View {
    let title: String
    let action: () -> Void

    public init(title: String = "Jump to latest", action: @escaping () -> Void) {
        self.title = title
        self.action = action
    }

    public var body: some View {
        Button(action: action) {
            Label(title, systemImage: "arrow.down.to.line")
                .labelStyle(.titleAndIcon)
        }
        .maButton(.ghost)
        .padding(MAStyle.Spacing.xs)
    }
}
