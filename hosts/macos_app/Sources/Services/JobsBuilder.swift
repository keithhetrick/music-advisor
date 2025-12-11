import Foundation
import MAQueue

enum JobsBuilder {
    static func makeJobs(from urls: [URL], baseCommand: String) -> [Job] {
        let baseParts = splitCommand(baseCommand)
        let baseOut = extractOutPath(from: baseParts)
        let filtered = urls.filter { isAudioFile($0) }
        let expanded = filtered.map { url in (url, groupID: UUID(), groupName: url.deletingLastPathComponent().lastPathComponent, groupRoot: url.deletingLastPathComponent().path) }
        return expanded.map { entry in
            let url = entry.0
            let outPath = baseOut ?? defaultSidecar(for: url)
            var parts = baseParts
            if let idx = parts.firstIndex(of: "--audio"), parts.indices.contains(idx + 1) {
                parts[idx + 1] = shellEscape(url.path)
            } else {
                parts.append(contentsOf: ["--audio", shellEscape(url.path)])
            }
            if let outIdx = parts.firstIndex(of: "--out"), parts.indices.contains(outIdx + 1) {
                parts[outIdx + 1] = shellEscape(outPath)
            } else {
                parts.append(contentsOf: ["--out", shellEscape(outPath)])
            }
            return Job(fileURL: url,
                       displayName: url.lastPathComponent,
                       groupID: entry.groupID,
                       groupName: entry.groupName,
                       groupRootPath: entry.groupRoot,
                       status: .pending,
                       sidecarPath: outPath,
                       errorMessage: nil,
                       preparedCommand: parts,
                       preparedOutPath: outPath)
        }
    }

    private static func splitCommand(_ text: String) -> [String] {
        var args: [String] = []
        var current = ""
        var inSingle = false
        var inDouble = false
        var isEscaping = false
        func push() {
            if !current.isEmpty {
                args.append(current)
                current = ""
            }
        }
        for ch in text {
            if isEscaping {
                current.append(ch)
                isEscaping = false
                continue
            }
            switch ch {
            case "\\":
                isEscaping = true
            case "'":
                if !inDouble { inSingle.toggle(); if !inSingle { continue } }
                else { current.append(ch) }
            case "\"":
                if !inSingle { inDouble.toggle(); if !inDouble { continue } }
                else { current.append(ch) }
            case " ":
                if inSingle || inDouble { current.append(ch) } else { push() }
            default:
                current.append(ch)
            }
        }
        push()
        return args
    }

    private static func shellEscape(_ text: String) -> String {
        if text.rangeOfCharacter(from: .whitespacesAndNewlines) != nil {
            return "\"" + text.replacingOccurrences(of: "\"", with: "\\\"") + "\""
        }
        return text
    }

    private static func extractOutPath(from parts: [String]) -> String? {
        if let idx = parts.firstIndex(of: "--out"), parts.indices.contains(idx + 1) {
            return parts[idx + 1]
        }
        return nil
    }

    private static func isAudioFile(_ url: URL) -> Bool {
        let ext = url.pathExtension.lowercased()
        let allowed: Set<String> = ["wav", "mp3", "m4a", "aif", "aiff", "flac", "ogg", "oga", "opus", "caf"]
        return allowed.contains(ext)
    }

    private static func defaultSidecar(for audioURL: URL) -> String {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        let sidecarDir = appDir.appendingPathComponent("sidecars", isDirectory: true)
        try? FileManager.default.createDirectory(at: sidecarDir, withIntermediateDirectories: true)
        let base = audioURL.deletingPathExtension().lastPathComponent
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let filename = "\(base)_\(timestamp).json"
        return sidecarDir.appendingPathComponent(filename).path
    }
}
