import SwiftUI

public struct MALineChart: View {
    public struct Series: Identifiable, Hashable {
        public let id = UUID()
        public let points: [Double]
        public let label: String
        public let color: Color
        public init(points: [Double], label: String = "", color: Color = MAStyle.ColorToken.primary) {
            self.points = points
            self.label = label
            self.color = color
        }
    }

    public let series: [Series]
    public let showDots: Bool
    public let showGrid: Bool

    public init(series: [Series], showDots: Bool = true, showGrid: Bool = true) {
        self.series = series
        self.showDots = showDots
        self.showGrid = showGrid
    }

    public var body: some View {
        GeometryReader { geo in
            ZStack {
                if showGrid {
                    grid(in: geo.size)
                }
                ForEach(series) { s in
                    linePath(for: s.points, in: geo.size)
                        .stroke(s.color, style: StrokeStyle(lineWidth: 2, lineJoin: .round))
                    if showDots {
                        dots(for: s.points, in: geo.size, color: s.color)
                    }
                }
            }
        }
    }

    private func normalized(_ points: [Double]) -> [Double] {
        guard let min = points.min(), let max = points.max(), max - min > 0 else {
            return points.map { _ in 0.5 }
        }
        return points.map { ($0 - min) / (max - min) }
    }

    private func linePath(for points: [Double], in size: CGSize) -> Path {
        let norm = normalized(points)
        let stepX = size.width / CGFloat(max(norm.count - 1, 1))
        return Path { path in
            for (idx, val) in norm.enumerated() {
                let x = CGFloat(idx) * stepX
                let y = size.height - CGFloat(val) * size.height
                if idx == 0 {
                    path.move(to: CGPoint(x: x, y: y))
                } else {
                    path.addLine(to: CGPoint(x: x, y: y))
                }
            }
        }
    }

    private func dots(for points: [Double], in size: CGSize, color: Color) -> some View {
        let norm = normalized(points)
        let stepX = size.width / CGFloat(max(norm.count - 1, 1))
        return ForEach(Array(norm.enumerated()), id: \.offset) { idx, val in
            let x = CGFloat(idx) * stepX
            let y = size.height - CGFloat(val) * size.height
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
                .position(x: x, y: y)
        }
    }

    private func grid(in size: CGSize) -> some View {
        let lines = 4
        return ZStack {
            ForEach(0...lines, id: \.self) { i in
                let y = size.height * CGFloat(i) / CGFloat(lines)
                Path { p in
                    p.move(to: CGPoint(x: 0, y: y))
                    p.addLine(to: CGPoint(x: size.width, y: y))
                }
                .stroke(MAStyle.ColorToken.border, style: StrokeStyle(lineWidth: 1, dash: [4]))
            }
        }
    }
}
