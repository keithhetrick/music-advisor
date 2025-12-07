import XCTest
@testable import MAStyle

final class MAStyleTests: XCTestCase {
    func testTokensAccessible() {
        _ = MAStyle.ColorToken.primary
        _ = MAStyle.Spacing.md
        _ = MAStyle.Radius.md
        _ = MAStyle.Typography.body
        _ = MAStyle.Borders.thin
    }

    func testChartsInit() {
        _ = MALineChart(series: [.init(points: [0.1, 0.2])])
        _ = MABarChart(values: [0.1, 0.5], labels: ["A", "B"])
        _ = MARadarChart(values: [0.2, 0.3, 0.4], labels: ["X", "Y", "Z"])
    }
}
