import XCTest
@testable import MAStyle

final class StyleTokenBehaviorTests: XCTestCase {
    func testSpacingValuesArePositive() {
        let spacing = MAStyle.theme.spacing
        XCTAssertGreaterThan(spacing.xs, 0)
        XCTAssertGreaterThan(spacing.sm, spacing.xs)
        XCTAssertGreaterThan(spacing.md, spacing.sm)
        XCTAssertGreaterThan(spacing.lg, spacing.md)
        XCTAssertGreaterThan(spacing.xl, spacing.lg)
        XCTAssertGreaterThan(spacing.xxl, spacing.xl)
    }

    func testRadiusValuesIncrease() {
        let radius = MAStyle.theme.radius
        XCTAssertGreaterThan(radius.md, radius.sm)
        XCTAssertGreaterThan(radius.lg, radius.md)
        XCTAssertGreaterThanOrEqual(radius.pill, radius.lg)
    }

    func testBordersPositive() {
        let borders = MAStyle.theme.borders
        XCTAssertGreaterThan(borders.thin, 0)
        XCTAssertGreaterThan(borders.regular, borders.thin)
    }

    func testThemeSwapApplies() {
        let original = MAStyle.theme
        MAStyle.theme = MAStyle.highContrastTheme
        defer { MAStyle.theme = original }

        XCTAssertEqual(MAStyle.theme.spacing.xs, MAStyle.highContrastTheme.spacing.xs)
        XCTAssertEqual(MAStyle.theme.radius.sm, MAStyle.highContrastTheme.radius.sm)
    }

    func testChartsHandleEmptyData() {
        _ = MALineChart(series: [])
        _ = MABarChart(values: [], labels: [])
        _ = MARadarChart(values: [], labels: [])
    }
}
