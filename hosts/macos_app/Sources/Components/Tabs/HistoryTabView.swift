import SwiftUI

struct HistoryTabView: View {
    @ObservedObject var store: AppStore
    let reloadHistory: () -> Void
    let revealSidecar: (String) -> Void
    let loadPreview: (String) -> Void
    @Binding var confirmClearHistory: Bool

    var body: some View {
        HistoryPanelView(
            items: store.state.historyItems,
            previews: store.state.historyPreviews,
            onRefresh: reloadHistory,
            onReveal: revealSidecar,
            onPreview: { path in loadPreview(path) },
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
    }
}
