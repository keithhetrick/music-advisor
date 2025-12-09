import SwiftUI

// MARK: - MetricTile
public struct MetricTile: View {
    public let label: String
    public let value: String
    public let icon: String?

    public init(label: String, value: String, icon: String? = nil) {
        self.label = label
        self.value = value
        self.icon = icon
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack(spacing: MAStyle.Spacing.xs) {
                if let icon {
                    Image(systemName: icon)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
                Text(label)
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            Text(value)
                .maText(.body)
        }
        .maMetric()
    }
}
