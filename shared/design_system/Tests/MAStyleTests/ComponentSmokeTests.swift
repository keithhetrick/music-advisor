import XCTest
import SwiftUI
@testable import MAStyle

final class ComponentSmokeTests: XCTestCase {
    func testStatusRowRenders() {
        let row = StatusRow<Text>(
            title: "Title",
            subtitle: "Subtitle",
            status: .info,
            progress: 0.5
        ) {
            Text("Trailing")
        }
        _ = row.body
    }

    func testBadgeCountRenders() {
        let badge = MABadgeCount(5, tone: .info)
        _ = badge.body
    }

    func testAlertBannerRenders() {
        let banner = AlertBanner(title: "Info",
                                 message: "Message",
                                 tone: .info,
                                 presentAsToast: true,
                                 autoDismissSeconds: 1.0,
                                 onClose: {})
        _ = banner.body
    }

    func testCollapsibleCardRenders() {
        let card = CollapsibleCard(initiallyExpanded: true,
                                   header: { Text("Header") },
                                   content: { Text("Content") })
        _ = card.body
    }

    func testToastProgressBarRenders() {
        let toast = ToastProgressBar(progress: 0.3, color: .blue)
        _ = toast.body
    }

    func testPromptBarRenders() {
        var text = "Hi"
        let view = PromptBar(text: Binding(get: { text }, set: { text = $0 }),
                             placeholder: "Say hi",
                             isThinking: false,
                             trailing: AnyView(Text("T")),
                             onSend: {},
                             onClear: {})
        _ = view.body
    }

    func testRailToggleRenders() {
        let toggle = RailToggle(state: .shown, compact: true, slideFromLeft: false, toggle: {})
        _ = toggle.body
    }
}
