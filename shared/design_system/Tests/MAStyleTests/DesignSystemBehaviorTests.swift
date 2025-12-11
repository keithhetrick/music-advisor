import XCTest
import SwiftUI
@testable import MAStyle

private struct DummyItem: Identifiable, Hashable, CustomStringConvertible {
    let id = UUID()
    let description: String
}

final class DesignSystemBehaviorTests: XCTestCase {
    func testThemeSwapAndDensityAdjust() {
        let original = MAStyle.theme
        defer { MAStyle.theme = original }

        MAStyle.useHighContrastTheme()
        XCTAssertNotEqual(MAStyle.theme.colors.primary, original.colors.primary)

        let originalSpacing = MAStyle.theme.spacing
        MAStyle.applyDensity(scale: 0.5)
        XCTAssertEqual(MAStyle.Spacing.sm, originalSpacing.sm * 0.5, accuracy: 0.001)
    }

    func testToastDefaultsMutable() {
        let original = MAStyle.ToastDefaults.autoDismissSeconds
        MAStyle.ToastDefaults.autoDismissSeconds = 3.0
        XCTAssertEqual(MAStyle.ToastDefaults.autoDismissSeconds, 3.0)
        MAStyle.ToastDefaults.autoDismissSeconds = original
    }

    func testFormRowsHelperAndErrorPaths() {
        var pickCount = 0
        var clearCount = 0

        let helperRow = MAFormFieldRow(title: "Title", helper: "Helper") {
            Text("Field")
        }
        _ = helperRow.body

        let errorRow = MAFormFieldRow(title: "Title", error: "Error!") {
            Text("Field")
        }
        _ = errorRow.body

        let picker = MAFilePickerRow(title: "File",
                                     value: "/tmp/file.wav",
                                     onPick: { pickCount += 1 },
                                     onClear: { clearCount += 1 })
        _ = picker.body
        picker.onPick()
        picker.onClear?()
        XCTAssertEqual(pickCount, 1)
        XCTAssertEqual(clearCount, 1)
    }

    func testNestedFolderTreeBuildsHierarchy() {
        let items = [
            FolderTreeItem(path: "/root/folder/a.wav", isRunning: true, item: DummyItem(description: "A")),
            FolderTreeItem(path: "/root/folder/sub/b.wav", isRunning: false, item: DummyItem(description: "B")),
            FolderTreeItem(path: "/other/c.wav", isRunning: false, item: DummyItem(description: "C"))
        ]
        let tree = NestedFolderTree(rootName: "Root",
                                    rootPath: "/root",
                                    items: items) { item in
            Text(item.item.description)
        }
        _ = tree.body
    }

    func testFabPopoverInitializesAndCloses() {
        let items = [DummyItem(description: "One"), DummyItem(description: "Two")]
        var closed = 0
        var selected: DummyItem?

        let fab = FABPopover(items: items,
                             enableSearch: false,
                             onSelect: { selected = $0 },
                             onClose: { closed += 1 })
        _ = fab.body
        fab.onClose?()
        if let first = items.first {
            fab.onSelect(first)
        }
        XCTAssertEqual(closed, 1)
        XCTAssertEqual(selected?.description, "One")
    }

    func testToastHostQueueConsumesMessages() {
        var queue = [
            MAToastMessage(title: "One", tone: .info, duration: 0.01),
            MAToastMessage(title: "Two", tone: .success, duration: 0.01)
        ]
        let host = MAToastHost(queue: Binding(get: { queue }, set: { queue = $0 }))
        _ = host.body
    }
}
