import SwiftUI

// MARK: - Copyable mono row (hover-only icon)
public struct CopyableMonoRow: View {
    let text: String
    let onCopy: () -> Void

    public init(_ text: String, onCopy: @escaping () -> Void) {
        self.text = text
        self.onCopy = onCopy
    }

    public var body: some View {
        HStack(alignment: .top, spacing: MAStyle.Spacing.xs) {
            Text(text)
                .font(MAStyle.Typography.bodyMono)
                .foregroundColor(MAStyle.ColorToken.muted)
                .frame(maxWidth: .infinity, alignment: .leading)
            HoverIconButton("doc.on.doc", action: onCopy)
        }
    }
}
