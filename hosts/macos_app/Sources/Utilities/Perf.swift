import os

enum Perf {
    static let previewLog = OSLog(subsystem: "com.bellweatherstudios.musicadvisor.macos", category: "preview")
    static let historyLog = OSLog(subsystem: "com.bellweatherstudios.musicadvisor.macos", category: "history")
    static let runnerLog = OSLog(subsystem: "com.bellweatherstudios.musicadvisor.macos", category: "runner")

    @discardableResult
    static func begin(_ log: OSLog, _ name: StaticString) -> OSSignpostID {
        let id = OSSignpostID(log: log)
        os_signpost(.begin, log: log, name: name, signpostID: id)
        return id
    }

    static func end(_ log: OSLog, _ name: StaticString, _ id: OSSignpostID) {
        os_signpost(.end, log: log, name: name, signpostID: id)
    }
}
