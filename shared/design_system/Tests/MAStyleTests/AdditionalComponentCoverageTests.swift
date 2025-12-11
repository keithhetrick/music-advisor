import XCTest
import SwiftUI
@testable import MAStyle

private struct ChipItem: Identifiable, Hashable, CustomStringConvertible {
    let id = UUID()
    let description: String
}

final class AdditionalComponentCoverageTests: XCTestCase {
    func testBreadcrumbsRenderAndActionsReachable() {
        var tapped = false
        let breadcrumbs = MABreadcrumbs([
            MABreadcrumb("Home"),
            MABreadcrumb("Details") { tapped = true }
        ])
        _ = breadcrumbs.body
        breadcrumbs.items.last?.action?()
        XCTAssertTrue(tapped)
    }

    func testCardHeaderVariants() {
        var fired = false
        let header = CardHeader(title: "Title",
                                subtitle: "Subtitle",
                                badge: "New",
                                actionTitle: "Tap",
                                action: { fired = true })
        _ = header.body
        header.action?()
        XCTAssertTrue(fired)

        let minimal = CardHeader(title: "Only Title")
        _ = minimal.body
    }

    func testChipRowSelectAndTrailingContent() {
        let items = [ChipItem(description: "One"), ChipItem(description: "Two")]
        var selected: ChipItem?
        let row = ChipRow(items: items,
                          style: .outline,
                          trailingContent: AnyView(Text("Trailing"))) { selected = $0 }
        _ = row.body
        if let second = row.items.last {
            row.onSelect(second)
        }
        XCTAssertEqual(selected?.description, "Two")
    }

    func testCloseableChipHandlesEnabledAndDisabled() {
        var closes = 0
        let active = MACloseableChip("Tag", color: .blue) { closes += 1 }
        _ = active.body
        active.onClose()

        let disabled = MACloseableChip("Tag", color: .blue, isDisabled: true) { closes += 1 }
        _ = disabled.body
        disabled.onClose()

        XCTAssertEqual(closes, 2) // onClose still callable even when disabled flag is set
    }

    func testMetricTileAndHeaderBarRender() {
        let withIcon = MetricTile(label: "Tempo", value: "120", icon: "metronome")
        _ = withIcon.body

        let withoutIcon = MetricTile(label: "Key", value: "C# Minor")
        _ = withoutIcon.body

        let header = HeaderBar(title: "Section", subtitle: "Subsection") {
            Button("Do nothing", action: {})
        }
        _ = header.body
    }

    func testScrollToBottomControllerStateFlow() {
        let controller = ScrollToBottomController()
        XCTAssertFalse(controller.showJump)

        controller.didScrollAway()
        XCTAssertTrue(controller.showJump)

        controller.jump()
        XCTAssertFalse(controller.showJump)
    }

    func testChatLogShowsJumpButtonWhenScrolledAway() {
        let controller = ScrollToBottomController()
        controller.didScrollAway()
        let view = ChatLogView(messages: ["Hi", "There"], scrollController: controller, onCopy: { _ in })
        _ = view.body
        XCTAssertTrue(controller.showJump)
    }

    func testCopyableMonoRowAndTableRowActions() {
        var copied = false
        let mono = CopyableMonoRow("hello world") { copied = true }
        _ = mono.body
        mono.onCopy()
        XCTAssertTrue(copied)

        var actionCount = 0
        let row = MATableRow(index: 1,
                             isSelected: true,
                             badgeCount: 3,
                             actionTitle: "Action",
                             action: { actionCount += 1 }) {
            Text("Row content")
        }
        _ = row.body
        row.action?()
        XCTAssertEqual(actionCount, 1)
    }

    func testChartsRenderAcrossConfigurations() {
        let bars = MABarChart(entries: [
            .init(label: "One", value: 1.0),
            .init(label: "Zero", value: 0.0, color: .green)
        ], showValues: false)
        _ = bars.body

        let flatLine = MALineChart(series: [.init(points: [2, 2], label: "Flat", color: .orange)],
                                   showDots: false,
                                   showGrid: false)
        _ = flatLine.body

        let variedLine = MALineChart(series: [.init(points: [0.2, 0.8, 0.4], label: "Varying")])
        _ = variedLine.body

        let radar = MARadarChart(axes: [
            .init(label: "Low", value: -0.5),
            .init(label: "High", value: 1.6),
            .init(label: "Mid", value: 0.4)
        ])
        _ = radar.body

        _ = MAChartsAvailability.swiftChartsAvailable
    }

    func testUtilitiesModifiersApply() {
        let icon = MAIcon("star.fill", size: 12, weight: .bold, color: .yellow)
        _ = icon.body

        let tag = MATag("Beta", icon: "bolt", tone: .warning)
        _ = tag.body

        let focusBinding = Binding.constant(true)
        let pickerBinding = Binding.constant(false)

        struct UtilityHarness: View {
            let focusBinding: Binding<Bool>
            let pickerBinding: Binding<Bool>
            var body: some View {
                VStack(spacing: 0) {
                    Text("Primary")
                        .maSectionTitle()
                        .maStackSpacing()
                        .maFocusRing(true)
                        .maActiveOutline(isActive: true)
                        .maAnimated(.easeInOut, value: true)
                        .maSegmentedStyle()
                        .maPickerHover()
                        .maToggleStyle()
                        .maSliderStyle()
                        .maFocusable(focusBinding)
                        .maPickerFocus(pickerBinding)
                        .maPulse(isActive: false)
                        .maSlideIn(from: .top, distance: 12, delay: 0)
                        .maFloat(amplitude: 2, duration: 0.1)
                        .maFadeIn(delay: 0)
                        .maShake(animatableData: 1.0)
                        .maActiveOutline(isActive: true)
                    SkeletonView(height: 8, cornerRadius: 3)
                    HoverIconButton("chevron.right", action: {})
                    VisualEffectBlur()
                }
            }
        }

        let harness = UtilityHarness(focusBinding: focusBinding, pickerBinding: pickerBinding)
        _ = harness.body
    }

    func testAlertToneMappingsAndBannerDismiss() {
        XCTAssertEqual(MAAlertTone.info.icon, "info.circle")
        XCTAssertEqual(MAAlertTone.success.icon, "checkmark.circle")
        XCTAssertEqual(MAAlertTone.warning.icon, "exclamationmark.triangle")
        XCTAssertEqual(MAAlertTone.danger.icon, "xmark.octagon")

        var dismissed = false
        let banner = MAAlertBanner(title: "Heads up",
                                   message: "Details",
                                   tone: .warning,
                                   dismissible: true,
                                   onDismiss: { dismissed = true })
        _ = banner.body
        banner.onDismiss?()
        XCTAssertTrue(dismissed)

        let toast = MAToastBanner(title: "Saved", tone: .success)
        _ = toast.body
    }

    func testModalActionsCloseBinding() {
        var presented = true
        var actionTriggered = false
        let modal = MAModal(isPresented: Binding(get: { presented }, set: { presented = $0 }),
                            style: .dialog,
                            title: "Confirm",
                            actions: [
                                MAModalAction("OK") { actionTriggered = true }
                            ]) {
            Text("Body")
        }

        _ = modal.body
        modal.actions.first?.action()
        XCTAssertTrue(actionTriggered)
        // Button tap would also set isPresented = false; the action closure alone should not mutate binding.
        XCTAssertTrue(presented)
    }

    func testModalAllStylesRender() {
        let binding = Binding.constant(true)
        let dialog = MAModal(isPresented: binding, style: .dialog, title: "Dialog") { Text("D") }
        _ = dialog.body

        let sheet = MAModal(isPresented: binding, style: .sheet, title: "Sheet") { Text("S") }
        _ = sheet.body

        let toast = MAModal(isPresented: binding, style: .toast, title: "Toast") { Text("T") }
        _ = toast.body

        let popup = MAModal(isPresented: binding, style: .popup, title: "Popup") { Text("P") }
        _ = popup.body
    }

    func testShowcaseSmoke() {
        let showcase = MAStyleShowcase()
        _ = showcase.body
    }
}
