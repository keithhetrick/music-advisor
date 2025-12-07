import SwiftUI

public struct MABarChart: View {
    public struct Entry: Identifiable, Hashable {
        public let id = UUID()
        public let label: String
        public let value: Double
        public let color: Color
        public init(label: String, value: Double, color: Color = MAStyle.ColorToken.primary) {
            self.label = label
            self.value = value
            self.color = color
        }
    }

    public let entries: [Entry]
    public let showValues: Bool

    public init(entries: [Entry], showValues: Bool = true) {
        self.entries = entries
        self.showValues = showValues
    }

    public init(values: [Double], labels: [String], showValues: Bool = true, color: Color = MAStyle.ColorToken.primary) {
        let count = min(values.count, labels.count)
        let zipped = zip(labels.prefix(count), values.prefix(count))
        self.entries = zipped.map { Entry(label: $0.0, value: $0.1, color: color) }
        self.showValues = showValues
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            ForEach(entries) { e in
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    HStack {
                        Text(e.label).maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                        Spacer()
                        if showValues {
                            Text(String(format: "%.1f", e.value)).maText(.caption)
                                .foregroundStyle(MAStyle.ColorToken.muted)
                        }
                    }
                    GeometryReader { geo in
                        let maxVal = max(entries.map { $0.value }.max() ?? 1, 0.0001)
                        let width = CGFloat(e.value / maxVal) * geo.size.width
                        RoundedRectangle(cornerRadius: MAStyle.Radius.sm)
                            .fill(LinearGradient(colors: [e.color.opacity(0.8), e.color.opacity(0.5)],
                                                 startPoint: .leading, endPoint: .trailing))
                            .frame(width: width, height: 10)
                    }
                    .frame(height: 12)
                }
            }
        }
    }
}
