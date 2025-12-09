import Foundation

/// Actor that loads sidecar previews off the main thread and coalesces duplicate requests.
actor HistoryPreviewLoader {
    private var inFlight: [String: Task<(HistoryPreview, Date?, Bool, Bool), Never>] = [:]

    func load(path: String) async -> (HistoryPreview, Date?, Bool, Bool) {
        if let task = inFlight[path] {
            return await task.value
        }
        let task = Task(priority: .utility) { [weak self] in
            let result = await HistoryPreviewLoader.readPreview(path: path)
            await self?.removeTask(for: path)
            return result
        }
        inFlight[path] = task
        return await task.value
    }

    private func removeTask(for path: String) {
        inFlight[path] = nil
    }

    private static func readPreview(path: String) async -> (HistoryPreview, Date?, Bool, Bool) {
        let signpost = Perf.begin(Perf.previewLog, "preview.parse")
        if Task.isCancelled { return (HistoryPreview(sidecar: "(cancelled)", rich: nil), nil, false, false) }
        let fm = FileManager.default
        let sidecarText: String = {
            if let data = fm.contents(atPath: path),
               let txt = String(data: data, encoding: .utf8) {
                return txt
            }
            return "(unreadable)"
        }()

        if Task.isCancelled { return (HistoryPreview(sidecar: sidecarText, rich: nil), nil, sidecarText == "(unreadable)", false) }

        var richText: String?
        var richFound = false
        var richPathUsed: String?
        let richPath = path.replacingOccurrences(of: ".json", with: ".client.rich.txt")

        if fm.fileExists(atPath: richPath),
           let data = fm.contents(atPath: richPath),
           let txt = String(data: data, encoding: .utf8) {
            richText = txt
            richFound = true
            richPathUsed = richPath
        } else {
            let baseName = URL(fileURLWithPath: path).deletingPathExtension().lastPathComponent
            var candidates: [String] = [baseName]
            if let lastUnderscore = baseName.lastIndex(of: "_") {
                let truncated = String(baseName[..<lastUnderscore])
                candidates.append(truncated)
            }
            let repoRoot = URL(fileURLWithPath: "/Users/keithhetrick/music-advisor")
            let featuresRoot = repoRoot.appendingPathComponent("data/features_output")
            if let enumerator = fm.enumerator(at: featuresRoot, includingPropertiesForKeys: nil) {
                var steps = 0
                let maxSteps = 5000
                for case let url as URL in enumerator {
                    if Task.isCancelled { break }
                    steps += 1
                    if steps > maxSteps { break }
                    for candidate in candidates {
                        if url.lastPathComponent == "\(candidate).client.rich.txt",
                           let data = try? Data(contentsOf: url),
                           let txt = String(data: data, encoding: .utf8) {
                            richText = txt
                            richFound = true
                            richPathUsed = url.path
                            break
                        }
                    }
                    if richFound { break }
                }
            }
        }

        let preview = HistoryPreview(sidecar: sidecarText,
                                     rich: richText,
                                     richFound: richFound,
                                     richPath: richPathUsed)
        let mtime = (try? fm.attributesOfItem(atPath: path)[.modificationDate] as? Date) ?? nil
        Perf.end(Perf.previewLog, "preview.parse", signpost)
        return (preview, mtime, sidecarText == "(unreadable)", !richFound)
    }
}
