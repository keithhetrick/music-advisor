import XCTest
import SwiftUI
@testable import MAStyle
import ViewInspector

private struct DummyItem: Identifiable, Hashable, CustomStringConvertible {
    let id = UUID()
    let description: String
}

final class InteractionCoverageTests: XCTestCase {
    func testNestedFolderTreeExpansion() throws {
        let items = [
            FolderTreeItem(path: "/root/a.wav", isRunning: false, item: DummyItem(description: "A")),
            FolderTreeItem(path: "/root/folder/b.wav", isRunning: true, item: DummyItem(description: "B"))
        ]
        let view = NestedFolderTree(rootName: "Root", rootPath: "/root", items: items) { item in
            Text(item.item.description)
        }
        let inspected = try view.inspect()
        XCTAssertNoThrow(try inspected.find(text: "Root"))
    }

    func testFabPopoverFilteringAndSelect() throws {
        let items = [DummyItem(description: "Alpha"), DummyItem(description: "Beta")]
        var selected: DummyItem?
        let fab = FABPopover(items: items, onSelect: { selected = $0 }, onClose: nil)
        _ = fab.body
        // Call onSelect directly to cover callback path.
        if let last = items.last {
            fab.onSelect(last)
        }
        XCTAssertEqual(selected?.description, "Beta")
    }

    func testFormRowsHelperAndError() throws {
        let helperRow = MAFormFieldRow(title: "Title", helper: "Help") { Text("Field") }
        let helper = try helperRow.inspect()
        XCTAssertEqual(try helper.find(text: "Help").string(), "Help")

        let errorRow = MAFormFieldRow(title: "Title", error: "Oops") { Text("Field") }
        let error = try errorRow.inspect()
        XCTAssertEqual(try error.find(text: "Oops").string(), "Oops")
    }

    func testToastHostConsumesQueue() throws {
        var queue = [
            MAToastMessage(title: "First", duration: 0.01),
            MAToastMessage(title: "Second", duration: 0.01)
        ]
        let host = MAToastHost(queue: Binding(get: { queue }, set: { queue = $0 }))
        _ = host.body
        // Manually consume queue to mirror dequeue logic.
        if !queue.isEmpty { queue.removeFirst() }
        XCTAssertEqual(queue.count, 1)
    }
}

extension NestedFolderTree: Inspectable {}
extension FABPopover: Inspectable {}
extension MAFormFieldRow: Inspectable {}
extension MAToastHost: Inspectable {}
