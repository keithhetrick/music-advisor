import SwiftUI

public struct MATableRow<Content: View>: View {
    let index: Int
    let isSelected: Bool
    let isDisabled: Bool
    let isFocused: Bool
    let badgeCount: Int?
    let actionTitle: String?
    let action: (() -> Void)?
    let content: Content

    public init(index: Int, isSelected: Bool = false, isDisabled: Bool = false, isFocused: Bool = false, badgeCount: Int? = nil, actionTitle: String? = nil, action: (() -> Void)? = nil, @ViewBuilder content: () -> Content) {
        self.index = index
        self.isSelected = isSelected
        self.isDisabled = isDisabled
        self.isFocused = isFocused
        self.badgeCount = badgeCount
        self.actionTitle = actionTitle
        self.action = action
        self.content = content()
    }

    public var body: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            content
            Spacer()
            if let badgeCount {
                MABadgeCount(badgeCount, tone: .info)
            }
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .maButton(.ghost)
                    .disabled(isDisabled)
            }
        }
        .maStripedRowStyle(index: index, isSelected: isSelected, isDisabled: isDisabled)
    }
}
