import SwiftUI

public struct MACloseableChip: View {
    let text: String
    let color: Color
    let isDisabled: Bool
    let onClose: () -> Void
    @State private var hovering = false

    public init(_ text: String, color: Color = MAStyle.ColorToken.primary, isDisabled: Bool = false, onClose: @escaping () -> Void) {
        self.text = text
        self.color = color
        self.isDisabled = isDisabled
        self.onClose = onClose
    }

    public var body: some View {
        HStack(spacing: MAStyle.Spacing.xs) {
            Text(text)
                .font(MAStyle.Typography.caption)
            Button(action: { onClose() }) {
                MAIcon("xmark", size: 10, weight: .semibold, color: color)
            }
            .buttonStyle(MAStyle.InteractiveButtonStyle(variant: .ghost))
            .disabled(isDisabled)
        }
        .padding(.horizontal, MAStyle.Spacing.sm)
        .padding(.vertical, MAStyle.Spacing.xs)
        .background(color.opacity(isDisabled ? 0.08 : 0.16))
        .foregroundColor(color)
        .cornerRadius(MAStyle.Radius.pill)
        .opacity(isDisabled ? 0.6 : 1.0)
        .scaleEffect(isDisabled ? 1.0 : (hovering ? 1.03 : 1.0))
        .onHover { hovering = $0 && !isDisabled }
        .animation(.easeOut(duration: 0.12), value: hovering)
    }
}
