import Foundation

/// Simple helper to throttle repeated alerts/toasts.
struct AlertThrottler {
    private var timestamps: [String: Date] = [:]
    private let lock = NSLock()

    mutating func shouldShow(key: String, minInterval: TimeInterval = 1.2) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        let now = Date()
        if let last = timestamps[key], now.timeIntervalSince(last) < minInterval {
            return false
        }
        timestamps[key] = now
        return true
    }
}
