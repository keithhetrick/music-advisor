import SwiftUI

#if canImport(Charts)
import Charts

@available(macOS 13.0, *)
public struct MASwiftLineChart: View {
    public struct Point: Identifiable {
        public let id = UUID()
        public let x: Double
        public let y: Double
    }
    let points: [Point]
    public init(values: [Double]) {
        self.points = values.enumerated().map { Point(x: Double($0.offset), y: $0.element) }
    }
    public var body: some View {
        Chart(points) { p in
            LineMark(x: .value("X", p.x), y: .value("Y", p.y))
                .foregroundStyle(MAStyle.ColorToken.primary)
        }
    }
}
#endif

public enum MAChartsAvailability {
    public static var swiftChartsAvailable: Bool {
        if #available(macOS 13.0, *), _isSwiftChartsAvailable {
            return true
        }
        return false
    }
    // compile-time flag
    private static var _isSwiftChartsAvailable: Bool {
        #if canImport(Charts)
        return true
        #else
        return false
        #endif
    }
}
