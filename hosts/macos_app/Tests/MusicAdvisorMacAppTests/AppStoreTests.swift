import XCTest
@testable import MusicAdvisorMacApp

@MainActor
final class AppStoreTests: XCTestCase {
    func testRoutePaneAndAlert() async {
        let store = AppStore()
        XCTAssertEqual(store.state.route, .run(.json))

        store.dispatch(.setRoute(.history))
        XCTAssertEqual(store.state.route.tab, .history)

        store.dispatch(.setRoute(store.state.route.updatingTab(.run)))
        XCTAssertEqual(store.state.route.tab, .run)
        store.dispatch(.setRoute(store.state.route.updatingRunPane(.stderr)))
        XCTAssertEqual(store.state.route.runPane, .stderr)

        let alert = AlertState(title: "oops", message: "error", level: .error)
        store.dispatch(.setAlert(alert))
        XCTAssertEqual(store.state.alert, alert)
        store.dispatch(.setAlert(nil))
        XCTAssertNil(store.state.alert)
    }

    func testMessagesCoalesce() async {
        let store = AppStore()
        for i in 0..<250 {
            store.dispatch(.appendMessage("msg \(i)"))
        }
        XCTAssertEqual(store.state.messages.count, 200)
        XCTAssertEqual(store.state.messages.first, "msg 50")
    }
}
