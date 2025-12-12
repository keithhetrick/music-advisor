import Foundation

final class Logger {
    private let queue = DispatchQueue(label: "taskconductor.logger")
    private let globalURL: URL?
    private let formatter: ISO8601DateFormatter
    private let rotationBytes: Int?
    private let lineHandler: (@Sendable (String) -> Void)?
    private let extraHandler: (@Sendable (TaskEvent) -> Void)?

    init(
        globalURL: URL?,
        rotationBytes: Int? = nil,
        lineHandler: (@Sendable (String) -> Void)? = nil,
        extraHandler: (@Sendable (TaskEvent) -> Void)? = nil
    ) {
        self.globalURL = globalURL
        self.rotationBytes = rotationBytes
        self.lineHandler = lineHandler
        self.extraHandler = extraHandler
        self.formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let url = globalURL {
            createParentDirectory(for: url)
        }
    }

    func log(event: TaskEvent, perTaskURL: URL?) {
        queue.async { [weak self] in
            guard let strongSelf = self else { return }
            let timestamp = strongSelf.formatter.string(from: Date())
            let line = "\(timestamp) \(strongSelf.describe(event))\n"
            if let url = strongSelf.globalURL {
                strongSelf.append(line: line, to: url)
            }
            if let url = perTaskURL {
                strongSelf.createParentDirectory(for: url)
                strongSelf.append(line: line, to: url)
            }
            strongSelf.lineHandler?(line)
            strongSelf.extraHandler?(event)
        }
    }

    private func append(line: String, to url: URL) {
        guard let data = line.data(using: .utf8) else { return }
        if !FileManager.default.fileExists(atPath: url.path) {
            FileManager.default.createFile(atPath: url.path, contents: nil)
        }
        do {
            if let rotationBytes, shouldRotate(url: url, threshold: rotationBytes) {
                rotate(url: url)
            }
            let handle = try FileHandle(forWritingTo: url)
            defer { try? handle.close() }
            try handle.seekToEnd()
            try handle.write(contentsOf: data)
        } catch {
            // Swallow logger errors; logging should never crash the host.
        }
    }

    private func shouldRotate(url: URL, threshold: Int) -> Bool {
        guard threshold > 0, let attrs = try? FileManager.default.attributesOfItem(atPath: url.path),
              let size = attrs[.size] as? NSNumber else { return false }
        return size.intValue >= threshold
    }

    private func rotate(url: URL) {
        let rotated = url.appendingPathExtension("1")
        try? FileManager.default.removeItem(at: rotated)
        try? FileManager.default.moveItem(at: url, to: rotated)
        FileManager.default.createFile(atPath: url.path, contents: nil)
    }

    private func createParentDirectory(for url: URL) {
        let dir = url.deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    }

    private func describe(_ event: TaskEvent) -> String {
        switch event {
        case let .started(id, command, workdir):
            return "[\(id)] started cmd=\(command.joined(separator: " ")) workdir=\(workdir ?? "-")"
        case let .stdout(id, line):
            return "[\(id)] stdout \(line)"
        case let .stderr(id, line):
            return "[\(id)] stderr \(line)"
        case let .finished(id, code, duration):
            return String(format: "[%@] finished exit=%d duration=%.3f", id.uuidString, code, duration)
        case let .failed(id, code, duration):
            return String(format: "[%@] failed exit=%d duration=%.3f", id.uuidString, code, duration)
        case let .canceled(id, duration):
            return String(format: "[%@] canceled duration=%.3f", id.uuidString, duration)
        case let .timeout(id, duration):
            return String(format: "[%@] timeout duration=%.3f", id.uuidString, duration)
        case let .retrying(id, attempt, delay):
            return String(format: "[%@] retrying attempt=%d delay=%.3f", id.uuidString, attempt, delay)
        case let .internalError(id, message):
            return "[\(id)] internalError \(message)"
        }
    }
}
