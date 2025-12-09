import Foundation

struct ChatContextResolver {
    struct Resolution {
        let path: String?
        let label: String
        let warning: String?
    }

    static func resolve(selection: String?,
                        sidecarPath: String?,
                        overridePath: String?,
                        historyItems: [SidecarItem],
                        previewCache: [String: (HistoryPreview, Date?)]) -> Resolution {
        // Default
        var label = "No context"
        var path: String? = nil
        var warning: String? = nil

        // If an explicit override is provided, use it first.
        if let overridePath {
            path = preferRich(path: overridePath, previewCache: previewCache)
            label = "History preview"
        }

        // Explicit selection
        if let sel = selection {
            switch sel {
            case "none":
                return Resolution(path: nil, label: "No context", warning: nil)
            case "last-run":
                if let p = sidecarPath {
                    label = "Last run"
                    path = preferRich(path: p, previewCache: previewCache)
                }
            case "history":
                if let overridePath {
                    label = "History preview"
                    path = preferRich(path: overridePath, previewCache: previewCache)
                } else if let p = sidecarPath ?? previewCache.values.first?.0.richPath {
                    label = "History preview"
                    path = preferRich(path: p, previewCache: previewCache)
                }
            default:
                if sel.hasPrefix("hist-") {
                    let uuidString = String(sel.dropFirst(5))
                    if let item = historyItems.first(where: { $0.id.uuidString == uuidString }) {
                        label = "History: \(item.name)"
                        path = preferRich(path: item.path, previewCache: previewCache)
                    }
                }
            }
        }

        // Fallback: use last-run if nothing selected and available
        if path == nil, let p = sidecarPath {
            label = "Last run"
            path = preferRich(path: p, previewCache: previewCache)
        }

        // Validate existence
        if let p = path, !FileManager.default.fileExists(atPath: p) {
            warning = "Context missing: \(URL(fileURLWithPath: p).lastPathComponent)"
            path = nil
            label = "No context (missing file)"
        }

        return Resolution(path: path, label: label, warning: warning)
    }

    private static func preferRich(path: String, previewCache: [String: (HistoryPreview, Date?)]) -> String {
        let fm = FileManager.default
        if let cached = previewCache[path]?.0.richPath, fm.fileExists(atPath: cached) {
            return cached
        }
        let url = URL(fileURLWithPath: path)
        let richCandidate = url.deletingPathExtension().appendingPathExtension("client.rich.txt")
        if fm.fileExists(atPath: richCandidate.path) { return richCandidate.path }
        return path
    }
}
