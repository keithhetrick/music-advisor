import SwiftUI
import MAStyle

struct HistorySplitView: View {
    @ObservedObject var store: AppStore
    let reloadHistory: () -> Void
    let revealSidecar: (String) -> Void
    let loadPreview: (String) -> Void
    let reRun: (SidecarItem?) -> Void
    let historySearchFocus: FocusState<Bool>.Binding
    @Binding var confirmClearHistory: Bool
    @State private var searchText: String = ""
    @State private var filterRichOnly: Bool = false
    @State private var selected: SidecarItem? = nil

    var body: some View {
        AdaptiveSplitView {
            filterBar
            HistoryPanelView(
                items: filteredItems,
                previews: store.state.historyPreviews,
                onRefresh: reloadHistory,
                onReveal: { path in
                    revealSidecar(path)
                    selected = store.state.historyItems.first(where: { $0.path == path })
                },
                onPreview: { path in
                    loadPreview(path)
                    selected = store.state.historyItems.first(where: { $0.path == path })
                },
                onClear: { confirmClearHistory = true }
            )
            .alert("Clear history?", isPresented: $confirmClearHistory) {
                Button("Cancel", role: .cancel) {}
                Button("Clear", role: .destructive) {
                    store.dispatch(.clearHistory)
                    try? SpecialActions.clearSidecarsOnDisk()
                    reloadHistory()
                }
            } message: {
                Text("This will remove saved sidecars from disk and clear in-memory history.")
            }
        } right: {
            HistoryPreviewCard(
                item: selected,
                preview: selected.flatMap { store.state.historyPreviews[$0.path] },
                onReveal: {
                    if let path = selected?.path { revealSidecar(path) }
                },
                onPreview: {
                    if let path = selected?.path { loadPreview(path) }
                },
                onRerun: { reRun(selected) }
            )
        }
    }

    private var filteredItems: [SidecarItem] {
        store.state.historyItems.filter { item in
            let matchesSearch = searchText.isEmpty || item.name.localizedCaseInsensitiveContains(searchText) || item.path.localizedCaseInsensitiveContains(searchText)
            let matchesRich = !filterRichOnly || store.state.historyPreviews[item.path]?.richFound == true
            return matchesSearch && matchesRich
        }
    }

    private var filterBar: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            TextField("Search history…", text: $searchText)
                .maInput()
                .focused(historySearchFocus)
                .accessibilityLabel("Search history")
            Toggle("Rich only", isOn: $filterRichOnly)
                .toggleStyle(.switch)
                .accessibilityLabel("Filter rich previews")
            Spacer()
        }
        .padding(.horizontal, MAStyle.Spacing.sm)
    }
}
