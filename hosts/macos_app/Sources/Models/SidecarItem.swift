import Foundation

struct SidecarItem: Identifiable, Hashable {
    let id = UUID()
    let path: String
    let name: String
    let modified: Date
}
