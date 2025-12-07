import SwiftUI

public struct MABadgeCount: View {
    let count: Int
    let tone: MAAlertTone
    public init(_ count: Int, tone: MAAlertTone = .info) {
        self.count = count
        self.tone = tone
    }
    public var body: some View {
        Text("\(count)")
            .font(MAStyle.Typography.caption)
            .padding(.horizontal, MAStyle.Spacing.xs)
            .padding(.vertical, MAStyle.Spacing.xs / 1.2)
            .background(tone.color.opacity(0.18))
            .foregroundColor(tone.color)
            .cornerRadius(MAStyle.Radius.pill)
    }
}
