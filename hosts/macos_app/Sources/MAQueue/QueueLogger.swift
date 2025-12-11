import Foundation

public enum QueueLogLevel: String {
    case debug
    case error
}

public struct QueueLogger {
    public static let shared = QueueLogger()

    private let queue = DispatchQueue(label: "com.musicadvisor.queue.logger")
    private let logURL = URL(fileURLWithPath: "/tmp/ma_queue_debug.log")
    private let formatter: ISO8601DateFormatter

    public init() {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        self.formatter = fmt
    }

    public func log(_ level: QueueLogLevel, _ message: String) {
        let timestamp = formatter.string(from: Date())
        let line = "\(timestamp) [\(level.rawValue.uppercased())] \(message)\n"
        queue.async {
            do {
                if FileManager.default.fileExists(atPath: self.logURL.path) {
                    let handle = try FileHandle(forWritingTo: self.logURL)
                    defer { try? handle.close() }
                    try handle.seekToEnd()
                    if let data = line.data(using: .utf8) {
                        try handle.write(contentsOf: data)
                    }
                } else {
                    try line.write(to: self.logURL, atomically: true, encoding: .utf8)
                }
            } catch {
                // Logging failures are non-fatal; best-effort only.
            }
        }
    }
}
