import SwiftUI

public struct MARadarChart: View {
    public struct Axis: Identifiable, Hashable {
        public let id = UUID()
        public let label: String
        public let value: Double // expected 0...1
        public init(label: String, value: Double) {
            self.label = label
            self.value = value
        }
    }

    public let axes: [Axis]
    public let strokeColor: Color
    public let fillColor: Color

    public init(axes: [Axis], strokeColor: Color = MAStyle.ColorToken.primary, fillColor: Color = MAStyle.ColorToken.primary.opacity(0.25)) {
        self.axes = axes
        self.strokeColor = strokeColor
        self.fillColor = fillColor
    }

    public init(values: [Double], labels: [String], strokeColor: Color = MAStyle.ColorToken.primary, fillColor: Color = MAStyle.ColorToken.primary.opacity(0.25)) {
        let count = min(values.count, labels.count)
        let axes = zip(labels.prefix(count), values.prefix(count)).map { Axis(label: $0.0, value: $0.1) }
        self.init(axes: axes, strokeColor: strokeColor, fillColor: fillColor)
    }

    public var body: some View {
        GeometryReader { geo in
            ZStack {
                grid(in: geo.size)
                shape(in: geo.size)
                    .fill(fillColor)
                shape(in: geo.size)
                    .stroke(strokeColor, lineWidth: 2)
                labels(in: geo.size)
            }
        }
    }

    private func shape(in size: CGSize) -> Path {
        guard !axes.isEmpty else { return Path() }

        let r = min(size.width, size.height) / 2 * 0.8
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let points: [CGPoint] = axes.enumerated().map { idx, axis in
            let angle = (Double(idx) / Double(axes.count)) * 2 * Double.pi - Double.pi/2
            let radius = r * axis.value.clamped(to: 0...1)
            let x = center.x + CGFloat(cos(angle)) * radius
            let y = center.y + CGFloat(sin(angle)) * radius
            return CGPoint(x: x, y: y)
        }

        return Path { path in
            guard let first = points.first else { return }
            path.move(to: first)
            for point in points.dropFirst() {
                path.addLine(to: point)
            }
            path.closeSubpath()
        }
    }

    private func grid(in size: CGSize) -> some View {
        let rings = 4
        let r = min(size.width, size.height) / 2 * 0.8
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        return ZStack {
            ForEach(0...rings, id: \.self) { i in
                let radius = r * CGFloat(i) / CGFloat(rings)
                Circle()
                    .stroke(MAStyle.ColorToken.border, style: StrokeStyle(lineWidth: 1, dash: [4]))
                    .frame(width: radius * 2, height: radius * 2)
                    .position(center)
            }
            ForEach(Array(axes.enumerated()), id: \.offset) { idx, _ in
                let angle = (Double(idx) / Double(axes.count)) * 2 * Double.pi - Double.pi/2
                let end = CGPoint(x: center.x + CGFloat(cos(angle)) * r,
                                  y: center.y + CGFloat(sin(angle)) * r)
                Path { p in
                    p.move(to: center)
                    p.addLine(to: end)
                }
                .stroke(MAStyle.ColorToken.border, style: StrokeStyle(lineWidth: 1, dash: [2]))
            }
        }
    }

    private func labels(in size: CGSize) -> some View {
        let r = min(size.width, size.height) / 2 * 0.92
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        return ForEach(Array(axes.enumerated()), id: \.offset) { idx, axis in
            let angle = (Double(idx) / Double(axes.count)) * 2 * Double.pi - Double.pi/2
            let point = CGPoint(x: center.x + CGFloat(cos(angle)) * r,
                                y: center.y + CGFloat(sin(angle)) * r)
            Text(axis.label)
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
                .position(point)
        }
    }
}

private extension Double {
    func clamped(to range: ClosedRange<Double>) -> Double {
        return min(max(self, range.lowerBound), range.upperBound)
    }
}
