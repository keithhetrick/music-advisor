import Foundation
import OSLog

public protocol TrackStore {
    func listTracks() throws -> [Track]
    func upsert(_ track: Track) throws
    func delete(id: UUID) throws
}

public protocol ArtistStore {
    func listArtists() throws -> [Artist]
    func upsert(_ artist: Artist) throws
    func delete(id: UUID) throws
}

public struct JsonTrackStore: TrackStore {
    private let url: URL
    private let logger = Logger(subsystem: "MusicAdvisorMacApp", category: "TrackStore")

    public init(url: URL) {
        self.url = url
    }

    public func listTracks() throws -> [Track] {
        guard FileManager.default.fileExists(atPath: url.path) else { return [] }
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode([Track].self, from: data)
    }

    public func upsert(_ track: Track) throws {
        var tracks = try listTracks().reduce(into: [UUID: Track]()) { dict, t in dict[t.id] = t }
        tracks[track.id] = track
        let all = Array(tracks.values)
        try persist(all)
    }

    public func delete(id: UUID) throws {
        var tracks = try listTracks().reduce(into: [UUID: Track]()) { dict, t in dict[t.id] = t }
        tracks.removeValue(forKey: id)
        let all = Array(tracks.values)
        try persist(all)
    }

    private func persist(_ tracks: [Track]) throws {
        let dir = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let data = try JSONEncoder().encode(tracks)
        try data.write(to: url, options: .atomic)
    }
}

public struct JsonArtistStore: ArtistStore {
    private let url: URL
    private let logger = Logger(subsystem: "MusicAdvisorMacApp", category: "ArtistStore")

    public init(url: URL) {
        self.url = url
    }

    public func listArtists() throws -> [Artist] {
        guard FileManager.default.fileExists(atPath: url.path) else { return [] }
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode([Artist].self, from: data)
    }

    public func upsert(_ artist: Artist) throws {
        var artists = try listArtists().reduce(into: [UUID: Artist]()) { dict, a in dict[a.id] = a }
        artists[artist.id] = artist
        let all = Array(artists.values)
        try persist(all)
    }

    public func delete(id: UUID) throws {
        var artists = try listArtists().reduce(into: [UUID: Artist]()) { dict, a in dict[a.id] = a }
        artists.removeValue(forKey: id)
        let all = Array(artists.values)
        try persist(all)
    }

    private func persist(_ artists: [Artist]) throws {
        let dir = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let data = try JSONEncoder().encode(artists)
        try data.write(to: url, options: .atomic)
    }
}
