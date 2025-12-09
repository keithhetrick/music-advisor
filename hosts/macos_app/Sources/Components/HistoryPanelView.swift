import SwiftUI
import MAStyle

struct HistoryPanelView: View {
    var items: [SidecarItem]
    var previews: [String: HistoryPreview]
    var onRefresh: () -> Void
    var onReveal: (String) -> Void
    var onPreview: (String) -> Void
    var onClear: () -> Void
    var onSelectContext: (String) -> Void = { _ in }
    @State private var isExpanded: [String: Bool] = [:]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            header
            if items.isEmpty {
                Text("No sidecars saved yet. Run a job or drop files to populate history.")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                        ForEach(items) { item in
                            historyRow(item: item)
                        }
                    }
                }
            }
        }
        .maCard()
        .maGlass()
    }

    private var header: some View {
        HStack(alignment: .center, spacing: MAStyle.Spacing.xs) {
            CardHeader(title: "History",
                       subtitle: "Saved sidecars",
                       badge: nil,
                       actionTitle: nil,
                       action: {})
            Spacer()
            HStack(spacing: MAStyle.Spacing.xs) {
                Button("Refresh") { onRefresh() }
                    .maButton(.ghost)
                    .accessibilityLabel("Refresh history")
                Button("Clear") { onClear() }
                    .maButton(.ghost)
                    .accessibilityLabel("Clear history")
            }
        }
    }

    @ViewBuilder
    private func historyRow(item: SidecarItem) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack(alignment: .center, spacing: MAStyle.Spacing.sm) {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    Text(item.name).maText(.body)
                    Text(item.modified.formatted(date: .abbreviated, time: .shortened))
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                    Text(item.path)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .lineLimit(1)
                }
                Spacer()
                if let preview = previews[item.path] {
                    Text(preview.richFound ? "Rich found" : "Rich missing")
                        .maBadge(preview.richFound ? .success : .warning)
                }
                Button("Reveal") { onReveal(item.path) }
                    .maButton(.ghost)
                Button(previews[item.path] == nil ? "Preview" : "Reload") { onPreview(item.path) }
                    .maButton(.ghost)
            }
            .contentShape(Rectangle())
            .onTapGesture {
                onSelectContext(item.path)
            }
            if let preview = previews[item.path] {
                DisclosureGroup(isExpanded: Binding(
                    get: { isExpanded[item.path] ?? false },
                    set: { isExpanded[item.path] = $0 }
                )) {
                    if !preview.sidecar.isEmpty {
                        codeBlock(title: "Sidecar JSON", text: preview.sidecar)
                    }
                    if let rich = preview.rich, !rich.isEmpty {
                        codeBlock(title: "Client Rich", text: rich)
                    } else {
                        codeBlock(title: "Client Rich", text: "(missing)")
                    }
                    if let richPath = preview.richPath {
                        Text(richPath)
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                    }
                } label: {
                    Text("Payload")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
                .padding(.top, MAStyle.Spacing.xs)
            }
        }
        .maCardInteractive()
    }

    @ViewBuilder
    private func codeBlock(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title).maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
            ScrollView {
                Text(text)
                    .font(MAStyle.Typography.bodyMono)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(MAStyle.Spacing.sm)
                    .maCardInteractive()
            }
            .frame(minHeight: 80)
        }
    }
}
