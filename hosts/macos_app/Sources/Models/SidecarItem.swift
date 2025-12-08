import Foundation

struct SidecarItem: Identifiable, Hashable, Codable {
    let id: UUID
    let path: String
    let name: String
    let modified: Date

    init(id: UUID = UUID(), path: String, name: String, modified: Date) {
        self.id = id
        self.path = path
        self.name = name
        self.modified = modified
    }
}
