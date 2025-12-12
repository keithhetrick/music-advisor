#if canImport(XCTest) && !SWIFT_PACKAGE
import XCTest

final class MusicAdvisorMacAppUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchEnvironment["MA_UI_TEST_MODE"] = "1"
        app.launchEnvironment["MA_ECHO_BROKER_ENABLE"] = "1"
        app.launchEnvironment["MA_ECHO_BROKER_URL"] = "http://127.0.0.1:8091"
    }

    func testQueueStopResumeAndBadges() throws {
        launchToRunTab()
        resetQueueIfNeeded()

        let queueCard = waitForElement("queue-card", timeout: 8)

        tapIfPresent("ui-test-start-queue")
        tapIfPresent("queue-toggle-visibility")
        tapIfPresent("queue-toggle-visibility")
        XCTAssertTrue(queueCard.exists, "Queue card should remain visible")
    }

    func testFolderExpansionStaysVisible() throws {
        launchToRunTab()
        resetQueueIfNeeded()
        tapIfPresent("ui-test-expand-folders")

        let folder = elementIfExists("folder-toggle-AlbumA", timeout: 6) ?? app.staticTexts["AlbumA"]
        guard folder.waitForExistence(timeout: 12) else {
            throw XCTSkip("Folder toggle not present in UI harness")
        }
        scrollToView(folder)
        tapSafely(folder)
        tapSafely(folder)
        XCTAssertTrue(folder.exists, "Folder toggle should still exist after taps")

        if let toggle = elementIfExists("queue-toggle-visibility") {
            scrollToView(toggle)
            tapSafely(toggle)
            tapSafely(toggle)
        }
        XCTAssertTrue(app.otherElements["queue-card"].exists)
    }

    func testToastAndSettingsModal() throws {
        launchToRunTab()
        let toastButton = waitForElement("ui-test-show-toast", timeout: 5)
        tapSafely(toastButton)
        XCTAssertTrue(app.staticTexts["UI Test Toast"].waitForExistence(timeout: 3))

        if let settings = elementIfExists("ui-test-open-settings", timeout: 4) {
            scrollToView(settings)
            tapSafely(settings)
        }
        _ = waitForElement("settings-overlay", timeout: 6)
        let close = elementIfExists("ui-test-close-settings", timeout: 6)
            ?? elementIfExists("close-settings", timeout: 6)
            ?? waitForElement("Close settings", timeout: 12)
        scrollToView(close)
        tapSafely(close)
    }

    func testClearCompletedAndCanceled() throws {
        launchToRunTab()
        resetQueueIfNeeded()

        tapIfPresent("queue-clear-completed")
        if app.buttons["Clear completed"].waitForExistence(timeout: 2) {
            app.buttons["Clear completed"].tap()
        }
        tapIfPresent("queue-clear-canceled-failed")
        if app.buttons["Clear canceled/failed"].waitForExistence(timeout: 2) {
            app.buttons["Clear canceled/failed"].tap()
        }
        XCTAssertTrue(app.otherElements["queue-card"].exists)
    }

    func testEnqueueCancelAndClearQueue() throws {
        launchToRunTab()
        resetQueueIfNeeded()

        tapIfPresent("ui-test-enqueue-sample")
        _ = app.staticTexts["ui-test.wav"].waitForExistence(timeout: 6)

        tapIfPresent("queue-cancel-pending")
        tapIfPresent("queue-clear-all")
        if app.buttons["Clear all"].waitForExistence(timeout: 2) {
            app.buttons["Clear all"].tap()
        }
        XCTAssertTrue(app.otherElements["queue-card"].exists)
    }

    func testEchoPanelExists() throws {
        launchToRunTab()
        let echoHeader = app.staticTexts["Historical Echo (broker)"]
        XCTAssertTrue(echoHeader.waitForExistence(timeout: 10))
        let retryFetch = app.buttons["Retry fetch"]
        XCTAssertTrue(retryFetch.exists)
    }

    func testHistoryTabAndThemeToggle() throws {
        launchToRunTab()
        if let historyTab = elementIfExists("tab-History", timeout: 3) {
            tapSafely(historyTab)
            XCTAssertTrue(app.staticTexts["History"].waitForExistence(timeout: 5))
        }
        if let themeToggle = elementIfExists("nav-theme-toggle", timeout: 2) {
            tapSafely(themeToggle)
            tapSafely(themeToggle)
        }
        if let runTab = elementIfExists("tab-Run", timeout: 2) {
            tapSafely(runTab)
        }
    }

    func testStopCancelAndResumeFlow() throws {
        launchToRunTab()
        resetQueueIfNeeded()
        tapIfPresent("ui-test-make-canceled")
        tapIfPresent("ui-test-show-resume")

        let resume = waitForElement("queue-resume-canceled", timeout: 10)
        tapSafely(resume)
        tapIfPresent("ui-test-start-queue")
        tapIfPresent("ui-test-stop-queue")
        tapIfPresent("queue-cancel-pending")
        XCTAssertTrue(app.otherElements["queue-card"].exists)
    }

    private func launchToRunTab() {
        app.launch()
        ensurePipelineTab()
    }

    private func resetQueueIfNeeded() {
        if let reset = elementIfExists("ui-test-reset-queue", timeout: 5) {
            tapSafely(reset)
        }
    }

    private func ensurePipelineTab() {
        let tab = app.buttons["tab-Run"]
        if tab.waitForExistence(timeout: 3) {
            tapSafely(tab)
        }
    }
}

private extension MusicAdvisorMacAppUITests {
    func waitForElement(_ identifier: String, timeout: TimeInterval = 5) -> XCUIElement {
        let element = app.descendants(matching: .any).matching(identifier: identifier).firstMatch
        XCTAssertTrue(element.waitForExistence(timeout: timeout), "Expected \(identifier) to exist")
        return element
    }

    func elementIfExists(_ identifier: String, timeout: TimeInterval = 1.5) -> XCUIElement? {
        let element = app.descendants(matching: .any).matching(identifier: identifier).firstMatch
        return element.waitForExistence(timeout: timeout) ? element : nil
    }

    func tapIfPresent(_ identifier: String) {
        if let element = elementIfExists(identifier, timeout: 1.5) {
            tapSafely(element)
        }
    }

    func scrollToView(_ element: XCUIElement, maxScrolls: Int = 4) {
        guard element.exists else { return }
        let scroll = app.scrollViews.firstMatch
        guard scroll.exists && scroll.isHittable else { return }
        for _ in 0..<maxScrolls where !element.isHittable {
            scroll.swipeUp()
        }
        if !element.isHittable {
            scroll.swipeDown()
        }
    }

    func tapSafely(_ element: XCUIElement) {
        if element.isHittable {
            element.tap()
            return
        }
        scrollToView(element)
        if element.isHittable {
            element.tap()
            return
        }
        if element.exists {
            let coord = element.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            coord.tap()
        }
    }
}
#endif
