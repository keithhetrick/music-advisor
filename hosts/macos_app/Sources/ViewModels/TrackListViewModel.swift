import Foundation

@MainActor
final class TrackListViewModel: ObservableObject {
    @Published var tracks: [Track] = []
    @Published var artists: [Artist] = []
    @Published var error: String = ""

    private let trackStore: TrackStore
    private let artistStore: ArtistStore

    init(trackStore: TrackStore, artistStore: ArtistStore) {
        self.trackStore = trackStore
        self.artistStore = artistStore
    }

    func load() {
        do {
            tracks = try trackStore.listTracks()
            artists = try artistStore.listArtists()
        } catch {
            self.error = "Load failed: \(error)"
        }
    }

    func addDummy() {
        do {
            let artist = Artist(name: "New Artist")
            try artistStore.upsert(artist)
            let track = Track(title: "New Track", artistId: artist.id)
            try trackStore.upsert(track)
            load()
        } catch {
            self.error = "Save failed: \(error)"
        }
    }

    func deleteTrack(_ track: Track) {
        do {
            try trackStore.delete(id: track.id)
            load()
        } catch {
            self.error = "Delete failed: \(error)"
        }
    }

    func update(track: Track, title: String, artistName: String) {
        do {
            var artistId = track.artistId
            if let existing = artists.first(where: { $0.name.caseInsensitiveCompare(artistName) == .orderedSame }) {
                artistId = existing.id
            } else {
                let newArtist = Artist(name: artistName.isEmpty ? "Unknown Artist" : artistName)
                try artistStore.upsert(newArtist)
                artistId = newArtist.id
            }
            var updated = track
            updated.title = title.isEmpty ? track.title : title
            updated.artistId = artistId
            try trackStore.upsert(updated)
            load()
        } catch {
            self.error = "Update failed: \(error)"
        }
    }

    func ingestDropped(urls: [URL]) {
        do {
            for url in urls {
                let base = url.deletingPathExtension().lastPathComponent
                let artistName = "Unknown Artist"
                let artist = artists.first(where: { $0.name == artistName }) ?? {
                    let newArtist = Artist(name: artistName)
                    try? artistStore.upsert(newArtist)
                    return newArtist
                }()
                if tracks.contains(where: { $0.title == base && $0.artistId == artist.id }) {
                    continue
                }
                let track = Track(title: base, artistId: artist.id, notes: url.path)
                try trackStore.upsert(track)
            }
            load()
        } catch {
            self.error = "Ingest failed: \(error)"
        }
    }

    func clearAll() {
        do {
            let existing = try trackStore.listTracks()
            for t in existing {
                try trackStore.delete(id: t.id)
            }
            load()
        } catch {
            self.error = "Clear failed: \(error)"
        }
    }
}
