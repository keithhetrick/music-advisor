import SwiftUI

public struct MAFormFieldRow<Content: View>: View {
    let title: String
    let helper: String?
    let error: String?
    let content: Content
    public init(title: String, helper: String? = nil, error: String? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.helper = helper
        self.error = error
        self.content = content()
    }
    public var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title)
                .font(MAStyle.Typography.caption)
                .foregroundColor(MAStyle.ColorToken.muted)
            content
            if let helper, error == nil {
                Text(helper)
                    .font(MAStyle.Typography.caption)
                    .foregroundColor(MAStyle.ColorToken.muted)
            }
            if let error {
                Text(error)
                    .font(MAStyle.Typography.caption)
                    .foregroundColor(MAStyle.ColorToken.danger)
            }
        }
    }
}

public struct MAFilePickerRow: View {
    let title: String
    let value: String
    let onPick: () -> Void
    let onClear: (() -> Void)?
    public init(title: String, value: String, onPick: @escaping () -> Void, onClear: (() -> Void)? = nil) {
        self.title = title
        self.value = value
        self.onPick = onPick
        self.onClear = onClear
    }
    public var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title)
                .font(MAStyle.Typography.caption)
                .foregroundColor(MAStyle.ColorToken.muted)
            HStack(spacing: MAStyle.Spacing.sm) {
                Text(value.isEmpty ? "No file selected" : value)
                    .font(MAStyle.Typography.caption)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .foregroundColor(MAStyle.ColorToken.muted)
                Spacer()
                Button("Browse…") { onPick() }
                    .maButton(.secondary)
                if let onClear, !value.isEmpty {
                    Button("Clear") { onClear() }
                        .maButton(.ghost)
                }
            }
        }
    }
}
