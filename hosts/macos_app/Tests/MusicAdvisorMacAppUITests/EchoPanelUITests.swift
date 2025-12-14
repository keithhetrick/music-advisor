import XCTest

final class EchoPanelUITests: XCTestCase {
    func testEchoPanelVisibleAndButtonsExist() throws {
        let app = XCUIApplication()
        app.launchEnvironment["MA_ECHO_BROKER_ENABLE"] = "1"
        app.launchEnvironment["MA_ECHO_BROKER_URL"] = "http://127.0.0.1:8091"
        app.launch()

        // Scroll to the Echo card
        let echoHeader = app.staticTexts["Historical Echo (broker)"]
        XCTAssertTrue(echoHeader.waitForExistence(timeout: 10))

        // Basic sanity: cache path label exists
        let cacheLabel = app.staticTexts.containing(NSPredicate(format: "label CONTAINS[c] 'Cache base:'")).element
        XCTAssertTrue(cacheLabel.exists)

        // Buttons should exist (they may be disabled when no data yet)
        let retryFetch = app.buttons["Retry fetch"]
        XCTAssertTrue(retryFetch.exists)

        let hideButton = app.buttons["Hide"]
        XCTAssertTrue(hideButton.exists)

        // Hide/Show toggle works
        hideButton.tap()
        let showButton = app.buttons["Show"]
        XCTAssertTrue(showButton.waitForExistence(timeout: 2))
    }
}
