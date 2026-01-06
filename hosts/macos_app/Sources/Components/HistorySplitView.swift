import SwiftUI
import MAStyle

struct HistorySplitView: View {
    @ObservedObject var store: AppStore
    let reloadHistory: () -> Void
    let revealSidecar: (String) -> Void
    let loadPreview: (String) -> Void
    let reRun: (SidecarItem?) -> Void
    let onSelectContext: (String) -> Void
    let historySearchFocus: FocusState<Bool>.Binding
    @Binding var confirmClearHistory: Bool
    var isLoading: Bool = false
    @State private var searchText: String = ""
    @State private var filterRichOnly: Bool = false
    @State private var selected: SidecarItem? = nil
    @State private var debouncedSearch: String = ""
    private let debounceInterval: Double = 0.25
    @State private var debounceTask: DispatchWorkItem?

    var body: some View {
        AdaptiveSplitView {
            VStack(spacing: MAStyle.Spacing.sm) {
                filterBar
                if isLoading {
                    skeletonList
                } else {
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
                        onClear: { confirmClearHistory = true },
                        onSelectContext: { path in
                            selected = store.state.historyItems.first(where: { $0.path == path })
                            onSelectContext(path)
                        }
                    )
                }
            }
            .maCard(enableLens: false)
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
                onRerun: { reRun(selected) },
                onViewEcho: {
                    if let name = selected?.name {
                        Task { await store.retryEchoFetch(trackId: name) }
                    }
                }
            )
            .maCard(enableLens: false)
        }
    }

    private var filteredItems: [SidecarItem] {
        store.state.historyItems.filter { item in
            let term = debouncedSearch.trimmingCharacters(in: .whitespacesAndNewlines)
            let matchesSearch = term.isEmpty || item.name.localizedCaseInsensitiveContains(term) || item.path.localizedCaseInsensitiveContains(term)
            let matchesRich = !filterRichOnly || store.state.historyPreviews[item.path]?.richFound == true
            return matchesSearch && matchesRich
        }
    }

    private var filterBar: some View {
            HStack(spacing: MAStyle.Spacing.sm) {
                TextField("Search history…", text: $searchText)
                    .maInput()
                    .focused(historySearchFocus)
                    .maFocusRing(historySearchFocus.wrappedValue)
                    .accessibilityLabel("Search history")
                    .overlay(alignment: .trailing) {
                        if !searchText.isEmpty {
                            Button {
                                searchText = ""
                                debouncedSearch = ""
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(MAStyle.ColorToken.muted)
                            }
                            .buttonStyle(.plain)
                            .padding(.trailing, MAStyle.Spacing.xs)
                            .accessibilityLabel("Clear search")
                            .maHoverLift()
                        }
                    }
                Toggle("Rich only", isOn: $filterRichOnly)
                    .maToggleStyle()
                    .accessibilityLabel("Filter rich previews")
                    .maFocusRing(historySearchFocus.wrappedValue)
                Spacer()
            }
        .maStackSpacing(MAStyle.Spacing.xs)
        .padding(.horizontal, MAStyle.Spacing.sm)
        .onChange(of: searchText) { newValue in
            debounceTask?.cancel()
            let task = DispatchWorkItem { debouncedSearch = newValue }
            debounceTask = task
            DispatchQueue.main.asyncAfter(deadline: .now() + debounceInterval, execute: task)
        }
    }

    private var skeletonList: some View {
        VStack(spacing: MAStyle.Spacing.sm) {
            ForEach(0..<4) { _ in
                SkeletonView(height: 56, cornerRadius: MAStyle.Radius.sm)
            }
        }
        .padding(.vertical, MAStyle.Spacing.xs)
    }
}
