import Foundation

public struct Artist: Codable, Identifiable, Hashable {
    public var id: UUID
    public var name: String
    public var aliases: [String]
    public var tags: [String]

    public init(id: UUID = UUID(),
                name: String,
                aliases: [String] = [],
                tags: [String] = []) {
        self.id = id
        self.name = name
        self.aliases = aliases
        self.tags = tags
    }
}
