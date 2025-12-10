import Foundation
import SQLite3
import OSLog

/// Single-source-of-truth store for tracks and artists backed by SQLite.
/// Keeps schema simple (JSON arrays for tags/aliases) and is macOS 12 compatible.
public final class SQLiteTrackStore: TrackStore, ArtistStore {
    private let db: OpaquePointer?
    private let logger = Logger(subsystem: "MusicAdvisorMacApp", category: "SQLiteTrackStore")

    public init(url: URL) throws {
        let dir = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

        var handle: OpaquePointer?
        let result = sqlite3_open(url.path, &handle)
        if result != SQLITE_OK || handle == nil {
            let message = SQLiteTrackStore.lastError(from: handle)
            sqlite3_close(handle)
            throw SQLiteStoreError.open(message: message)
        }
        self.db = handle
        try createSchema()
    }

    deinit {
        sqlite3_close(db)
    }

    // MARK: - TrackStore
    public func listTracks() throws -> [Track] {
        let sql = "SELECT id, title, artist_id, bpm, key, notes, tags FROM tracks ORDER BY title;"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw SQLiteStoreError.prepare(message: SQLiteTrackStore.lastError(from: db))
        }
        defer { sqlite3_finalize(statement) }

        var tracks: [Track] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            guard
                let idText = sqlite3_column_text(statement, 0),
                let titleText = sqlite3_column_text(statement, 1),
                let artistIdText = sqlite3_column_text(statement, 2)
            else { continue }

            let id = UUID(uuidString: String(cString: idText)) ?? UUID()
            let title = String(cString: titleText)
            let artistId = UUID(uuidString: String(cString: artistIdText)) ?? UUID()
            let bpm = sqlite3_column_type(statement, 3) == SQLITE_NULL ? nil : sqlite3_column_double(statement, 3)
            let key = sqlite3_column_type(statement, 4) == SQLITE_NULL ? nil : String(cString: sqlite3_column_text(statement, 4))
            let notes = sqlite3_column_type(statement, 5) == SQLITE_NULL ? nil : String(cString: sqlite3_column_text(statement, 5))
            let tagsJSON = sqlite3_column_type(statement, 6) == SQLITE_NULL ? "[]" : String(cString: sqlite3_column_text(statement, 6))
            let tags = (try? JSONDecoder().decode([String].self, from: Data(tagsJSON.utf8))) ?? []

            let track = Track(id: id, title: title, artistId: artistId, bpm: bpm, key: key, notes: notes, tags: tags)
            tracks.append(track)
        }
        return tracks
    }

    public func upsert(_ track: Track) throws {
        let sql = """
        INSERT INTO tracks (id, title, artist_id, bpm, key, notes, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            artist_id=excluded.artist_id,
            bpm=excluded.bpm,
            key=excluded.key,
            notes=excluded.notes,
            tags=excluded.tags;
        """
        let stmt = try prepare(sql)
        defer { sqlite3_finalize(stmt) }
        bind(uuid: track.id, index: 1, stmt: stmt)
        bind(text: track.title, index: 2, stmt: stmt)
        bind(uuid: track.artistId, index: 3, stmt: stmt)
        bind(optionalDouble: track.bpm, index: 4, stmt: stmt)
        bind(optionalText: track.key, index: 5, stmt: stmt)
        bind(optionalText: track.notes, index: 6, stmt: stmt)
        let tagsJSON = (try? String(data: JSONEncoder().encode(track.tags), encoding: .utf8)) ?? "[]"
        bind(text: tagsJSON, index: 7, stmt: stmt)
        try execute(stmt)
    }

    public func delete(id: UUID) throws {
        // Attempt to delete both a track and an artist with this id; covers both protocols.
        let deleteTrackSQL = "DELETE FROM tracks WHERE id = ?;"
        let deleteArtistSQL = "DELETE FROM artists WHERE id = ?;"

        // Track delete
        do {
            let stmt = try prepare(deleteTrackSQL)
            defer { sqlite3_finalize(stmt) }
            bind(uuid: id, index: 1, stmt: stmt)
            try execute(stmt)
        } catch {
            logger.error("Failed to delete track id \(id.uuidString, privacy: .public): \(String(describing: error), privacy: .public)")
            throw error
        }

        // Artist delete
        do {
            let stmt = try prepare(deleteArtistSQL)
            defer { sqlite3_finalize(stmt) }
            bind(uuid: id, index: 1, stmt: stmt)
            try execute(stmt)
        } catch {
            logger.error("Failed to delete artist id \(id.uuidString, privacy: .public): \(String(describing: error), privacy: .public)")
            throw error
        }
    }

    // MARK: - ArtistStore
    public func listArtists() throws -> [Artist] {
        let sql = "SELECT id, name, aliases, tags FROM artists ORDER BY name;"
        let stmt = try prepare(sql)
        defer { sqlite3_finalize(stmt) }

        var artists: [Artist] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            guard
                let idText = sqlite3_column_text(stmt, 0),
                let nameText = sqlite3_column_text(stmt, 1)
            else { continue }
            let aliasesJSON = sqlite3_column_type(stmt, 2) == SQLITE_NULL ? "[]" : String(cString: sqlite3_column_text(stmt, 2))
            let tagsJSON = sqlite3_column_type(stmt, 3) == SQLITE_NULL ? "[]" : String(cString: sqlite3_column_text(stmt, 3))
            let id = UUID(uuidString: String(cString: idText)) ?? UUID()
            let name = String(cString: nameText)
            let aliases = (try? JSONDecoder().decode([String].self, from: Data(aliasesJSON.utf8))) ?? []
            let tags = (try? JSONDecoder().decode([String].self, from: Data(tagsJSON.utf8))) ?? []
            let artist = Artist(id: id, name: name, aliases: aliases, tags: tags)
            artists.append(artist)
        }
        return artists
    }

    public func upsert(_ artist: Artist) throws {
        let sql = """
        INSERT INTO artists (id, name, aliases, tags)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            aliases=excluded.aliases,
            tags=excluded.tags;
        """
        let stmt = try prepare(sql)
        defer { sqlite3_finalize(stmt) }
        bind(uuid: artist.id, index: 1, stmt: stmt)
        bind(text: artist.name, index: 2, stmt: stmt)
        let aliasesJSON = (try? String(data: JSONEncoder().encode(artist.aliases), encoding: .utf8)) ?? "[]"
        let tagsJSON = (try? String(data: JSONEncoder().encode(artist.tags), encoding: .utf8)) ?? "[]"
        bind(text: aliasesJSON, index: 3, stmt: stmt)
        bind(text: tagsJSON, index: 4, stmt: stmt)
        try execute(stmt)
    }

    // MARK: - Schema
    private func createSchema() throws {
        let createArtists = """
        CREATE TABLE IF NOT EXISTS artists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            aliases TEXT,
            tags TEXT
        );
        """
        let createTracks = """
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            artist_id TEXT NOT NULL,
            bpm REAL,
            key TEXT,
            notes TEXT,
            tags TEXT,
            FOREIGN KEY(artist_id) REFERENCES artists(id)
        );
        """
        try execute(sql: createArtists)
        try execute(sql: createTracks)
    }

    // MARK: - Helpers
    private func prepare(_ sql: String) throws -> OpaquePointer? {
        var stmt: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) != SQLITE_OK {
            throw SQLiteStoreError.prepare(message: SQLiteTrackStore.lastError(from: db))
        }
        return stmt
    }

    private func execute(_ stmt: OpaquePointer?) throws {
        guard sqlite3_step(stmt) == SQLITE_DONE else {
            throw SQLiteStoreError.execute(message: SQLiteTrackStore.lastError(from: db))
        }
    }

    private func execute(sql: String) throws {
        var err: UnsafeMutablePointer<Int8>?
        if sqlite3_exec(db, sql, nil, nil, &err) != SQLITE_OK {
            let message = err.map { String(cString: $0) } ?? "unknown error"
            sqlite3_free(err)
            throw SQLiteStoreError.execute(message: message)
        }
    }

    private func bind(text: String, index: Int32, stmt: OpaquePointer?) {
        sqlite3_bind_text(stmt, index, text, -1, SQLITE_TRANSIENT)
    }

    private func bind(optionalText: String?, index: Int32, stmt: OpaquePointer?) {
        if let text = optionalText {
            bind(text: text, index: index, stmt: stmt)
        } else {
            sqlite3_bind_null(stmt, index)
        }
    }

    private func bind(optionalDouble: Double?, index: Int32, stmt: OpaquePointer?) {
        if let value = optionalDouble {
            sqlite3_bind_double(stmt, index, value)
        } else {
            sqlite3_bind_null(stmt, index)
        }
    }

    private func bind(uuid: UUID, index: Int32, stmt: OpaquePointer?) {
        bind(text: uuid.uuidString, index: index, stmt: stmt)
    }

    private static func lastError(from handle: OpaquePointer?) -> String {
        guard let msg = sqlite3_errmsg(handle) else { return "unknown sqlite error" }
        return String(cString: msg)
    }
}

public enum SQLiteStoreError: Error, LocalizedError {
    case open(message: String)
    case prepare(message: String)
    case execute(message: String)

    public var errorDescription: String? {
        switch self {
        case .open(let message): return "SQLite open failed: \(message)"
        case .prepare(let message): return "SQLite prepare failed: \(message)"
        case .execute(let message): return "SQLite execute failed: \(message)"
        }
    }
}

// SQLite helper for binding transient strings.
private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
