import Foundation

public struct Track: Codable, Identifiable, Hashable {
    public var id: UUID
    public var title: String
    public var artistId: UUID
    public var bpm: Double?
    public var key: String?
    public var notes: String?
    public var tags: [String]

    public init(id: UUID = UUID(),
                title: String,
                artistId: UUID,
                bpm: Double? = nil,
                key: String? = nil,
                notes: String? = nil,
                tags: [String] = []) {
        self.id = id
        self.title = title
        self.artistId = artistId
        self.bpm = bpm
        self.key = key
        self.notes = notes
        self.tags = tags
    }
}
