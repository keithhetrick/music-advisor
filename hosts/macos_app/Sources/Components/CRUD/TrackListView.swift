import SwiftUI
import MAStyle

struct TrackListView: View {
    @ObservedObject var viewModel: TrackListViewModel
    @State private var titleEdits: [UUID: String] = [:]
    @State private var artistEdits: [UUID: String] = [:]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text("Tracks").maText(.headline)
                Spacer()
                Button("Add dummy") { viewModel.addDummy() }
                    .maButton(.secondary)
                Button("Clear") { viewModel.clearAll() }
                    .maButton(.ghost)
            }
            if !viewModel.error.isEmpty {
                Text(viewModel.error).maBadge(.danger)
            }
            List {
                ForEach(viewModel.tracks) { track in
                    HStack {
                        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                            TextField("Title", text: Binding(
                                get: { titleEdits[track.id] ?? track.title },
                                set: { titleEdits[track.id] = $0 }
                            ))
                            .maInput()

                            TextField("Artist", text: Binding(
                                get: {
                                    let current = viewModel.artists.first(where: { $0.id == track.artistId })?.name ?? "Unknown Artist"
                                    return artistEdits[track.id] ?? current
                                },
                                set: { artistEdits[track.id] = $0 }
                            ))
                            .maInput()
                            .font(.caption)
                        }
                        Spacer()
                        Button("Save") {
                            let title = titleEdits[track.id] ?? track.title
                            let artist = artistEdits[track.id] ?? (viewModel.artists.first(where: { $0.id == track.artistId })?.name ?? "Unknown Artist")
                            viewModel.update(track: track, title: title, artistName: artist)
                        }
                        .maButton(.ghost)
                        Button {
                            viewModel.deleteTrack(track)
                        } label: {
                            Image(systemName: "trash")
                        }
                        .buttonStyle(.plain)
                    }
                    .modifier(ListRowStyling())
                }
            }
            .modifier(ListBackgroundStyling())
            .frame(height: 200)
        }
        .maCard()
        .onAppear {
            viewModel.load()
        }
        .onChange(of: viewModel.tracks) { _ in
            // Keep edits in sync when list changes.
            titleEdits = [:]
            artistEdits = [:]
        }
    }
}
