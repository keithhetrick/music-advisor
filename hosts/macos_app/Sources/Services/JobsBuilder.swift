import Foundation
import MAQueue

struct DropEntry {
    let url: URL
    let groupID: UUID?
    let groupName: String?
    let groupRoot: String?
}

enum JobsBuilder {
    static func makeJobs(from entries: [DropEntry], baseCommand: String) -> [Job] {
        let baseParts = splitCommand(baseCommand)
        let isAutomator = baseParts.first?.hasSuffix("automator.sh") ?? false
        let baseOut = extractOutPath(from: baseParts)
        let filtered = entries.filter { isAudioFile($0.url) }
        return filtered.map { entry in
            let url = entry.url
            var outPath: String? = nil
            var parts = baseParts

            if isAutomator {
                // Automator expects positional audio paths; do not inject --audio/--out.
                parts.append(url.path)
            } else {
                outPath = buildOutPath(for: url, baseOut: baseOut)
                if let idx = parts.firstIndex(of: "--audio"), parts.indices.contains(idx + 1) {
                    parts[idx + 1] = url.path
                } else {
                    parts.append(contentsOf: ["--audio", url.path])
                }
                if let outIdx = parts.firstIndex(of: "--out"), parts.indices.contains(outIdx + 1) {
                    parts[outIdx + 1] = outPath ?? ""
                } else if let outPath {
                    parts.append(contentsOf: ["--out", outPath])
                }
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

    private static func extractOutPath(from parts: [String]) -> String? {
        if let idx = parts.firstIndex(of: "--out"), parts.indices.contains(idx + 1) {
            return parts[idx + 1]
        }
        return nil
    }

    /// Compute a unique per-job out path. If a base --out was provided, reuse its directory/name stem
    /// but stamp a unique filename. Otherwise, place sidecars under Application Support/sidecars.
    private static func buildOutPath(for audioURL: URL, baseOut: String?) -> String {
        let fm = FileManager.default
        let sidecarDir = defaultSidecarDirectory()

        let stem: String
        let ext: String
        if let baseOut {
            let baseURL = URL(fileURLWithPath: baseOut)
            let baseStem = baseURL.deletingPathExtension().lastPathComponent
            stem = baseStem.isEmpty ? audioURL.deletingPathExtension().lastPathComponent : baseStem
            ext = baseURL.pathExtension.isEmpty ? "json" : baseURL.pathExtension
        } else {
            stem = audioURL.deletingPathExtension().lastPathComponent
            ext = "json"
        }

        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let filename = "\(stem)_\(timestamp).\(ext)"
        try? fm.createDirectory(at: sidecarDir, withIntermediateDirectories: true)
        return sidecarDir.appendingPathComponent(filename).path
    }

    private static func isAudioFile(_ url: URL) -> Bool {
        let ext = url.pathExtension.lowercased()
        let allowed: Set<String> = ["wav", "mp3", "m4a", "aif", "aiff", "flac", "ogg", "oga", "opus", "caf"]
        return allowed.contains(ext)
    }

    private static func defaultSidecar(for audioURL: URL) -> String {
        let sidecarDir = defaultSidecarDirectory()
        try? FileManager.default.createDirectory(at: sidecarDir, withIntermediateDirectories: true)
        let base = audioURL.deletingPathExtension().lastPathComponent
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let filename = "\(base)_\(timestamp).json"
        return sidecarDir.appendingPathComponent(filename).path
    }

    private static func defaultSidecarDirectory() -> URL {
        let supportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = supportDir.appendingPathComponent("MusicAdvisorMacApp", isDirectory: true)
        return appDir.appendingPathComponent("sidecars", isDirectory: true)
    }
}
