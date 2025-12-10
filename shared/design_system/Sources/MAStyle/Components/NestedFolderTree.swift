import SwiftUI
import MAStyle

/// Item model for nested folder trees.
public struct FolderTreeItem<Item>: Identifiable {
    public let id: UUID
    public let path: String
    public let isRunning: Bool
    public let item: Item
    public init(id: UUID = UUID(), path: String, isRunning: Bool, item: Item) {
        self.id = id
        self.path = path
        self.isRunning = isRunning
        self.item = item
    }
}

/// Renders a nested folder tree from a list of items with paths.
public struct NestedFolderTree<Item, Leaf: View>: View {
    let rootName: String
    let rootPath: String
    let items: [FolderTreeItem<Item>]
    let leafContent: (FolderTreeItem<Item>) -> Leaf

    @State private var expanded: [String: Bool] = [:]

    public init(rootName: String,
                rootPath: String,
                items: [FolderTreeItem<Item>],
                leafContent: @escaping (FolderTreeItem<Item>) -> Leaf) {
        self.rootName = rootName
        self.rootPath = rootPath
        self.items = items
        self.leafContent = leafContent
    }

    public var body: some View {
        let tree = buildTree(from: items, rootName: rootName, rootPath: rootPath)
        folderNodeView(tree, depth: 0)
    }

    private struct Node: Identifiable {
        let id = UUID()
        let name: String
        let path: String
        var folders: [Node] = []
        var files: [FolderTreeItem<Item>] = []
    }

    private func buildTree(from items: [FolderTreeItem<Item>], rootName: String, rootPath: String) -> Node {
        var root = Node(name: rootName, path: rootPath)
        for item in items {
            let relative = relativePath(fullPath: item.path, rootPath: rootPath)
            let components = relative.split(separator: "/").map(String.init)
            insert(item: item, components: components, into: &root)
        }
        return root
    }

    private func relativePath(fullPath: String, rootPath: String) -> String {
        if fullPath.hasPrefix(rootPath) {
            let trimmed = String(fullPath.dropFirst(rootPath.count)).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            return trimmed.isEmpty ? URL(fileURLWithPath: fullPath).lastPathComponent : trimmed
        }
        return URL(fileURLWithPath: fullPath).lastPathComponent
    }

    private func insert(item: FolderTreeItem<Item>, components: [String], into node: inout Node) {
        guard let first = components.first else {
            node.files.append(item)
            return
        }
        if components.count == 1 {
            node.files.append(item)
            return
        }
        let folder = first
        let remaining = Array(components.dropFirst())
        if let idx = node.folders.firstIndex(where: { $0.name == folder }) {
            var child = node.folders[idx]
            insert(item: item, components: remaining, into: &child)
            node.folders[idx] = child
        } else {
            var child = Node(name: folder, path: node.path + "/" + folder)
            insert(item: item, components: remaining, into: &child)
            node.folders.append(child)
            node.folders.sort { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
        }
    }

    private func runningCount(in node: Node) -> Int {
        let selfCount = node.files.filter { $0.isRunning }.count
        return selfCount + node.folders.reduce(0) { $0 + runningCount(in: $1) }
    }

    private func totalFiles(in node: Node) -> Int {
        node.files.count + node.folders.reduce(0) { $0 + totalFiles(in: $1) }
    }

    private func folderNodeView(_ node: Node, depth: Int) -> some View {
        let key = node.path
        let expandedBinding = Binding(get: { expanded[key, default: true] },
                                      set: { expanded[key] = $0 })
        let running = runningCount(in: node)
        let isActive = running > 0 && !expandedBinding.wrappedValue

        return AnyView(
            DisclosureGroup(isExpanded: expandedBinding) {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    ForEach(node.folders) { child in
                        folderNodeView(child, depth: depth + 1)
                    }
                    ForEach(node.files) { item in
                        leafContent(item)
                    }
                }
                .padding(.leading, MAStyle.Spacing.sm)
            } label: {
                GroupedRow(isActive: false) {
                    HStack {
                        Image(systemName: "folder.fill")
                        Text(node.name)
                            .maText(.body)
                        Spacer()
                        Text("\(totalFiles(in: node)) file(s)")
                            .maBadge(.info)
                    }
                    .padding(.leading, CGFloat(depth) * MAStyle.Spacing.md)
                    .contentShape(RoundedRectangle(cornerRadius: MAStyle.Radius.md))
                }
            }
            .maCard()
            .clipShape(RoundedRectangle(cornerRadius: MAStyle.Radius.md))
            .maSheen(isActive: isActive, duration: 3.0, highlight: Color.white.opacity(0.08))
            .id(isActive ? "\(key)-\(running)" : key)
        )
    }
}
