import XCTest
import SwiftUI
@testable import MAStyle

final class ChartInitCoverageTests: XCTestCase {
    func testBarChartEntryInitWithLabels() {
        let chart = MABarChart(values: [1.0, 2.5, 3.0], labels: ["A", "B", "C", "Extra"])
        XCTAssertEqual(chart.entries.count, 3)
        XCTAssertEqual(chart.entries.first?.label, "A")
        XCTAssertEqual(chart.entries.last?.value, 3.0)
        _ = chart.body
    }

    func testLineChartSeriesConfigs() {
        let series = [
            MALineChart.Series(points: [0.0, 0.0], label: "Flat", color: .red),
            MALineChart.Series(points: [1.0, 3.0, 2.0], label: "UpDown", color: .green)
        ]
        let chart = MALineChart(series: series, showDots: false, showGrid: false)
        XCTAssertEqual(chart.series.count, 2)
        _ = chart.body
    }

    func testRadarChartClampsValues() {
        let chart = MARadarChart(values: [-1.0, 0.5, 2.0], labels: ["Low", "Mid", "High"])
        XCTAssertEqual(chart.axes.count, 3)
        _ = chart.body
    }

    func testSwiftChartsAvailabilityFlag() {
        _ = MAChartsAvailability.swiftChartsAvailable
    }
}
