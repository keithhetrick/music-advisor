import Foundation
import os

/// Lightweight bridge to the Python chat router in tools/chat.
/// Runs off the main thread, with PYTHONPATH set to repo root.
actor ChatService: ChatProvider {
    private let runner = RunnerService()
    private let log = OSLog(subsystem: "com.bellweatherstudios.musicadvisor.chat", category: "chat")
    private let config: ChatProviderConfig
    private var lastSent: Date?

    init(config: ChatProviderConfig = .defaultConfig()) {
        self.config = config
    }

    func send(prompt: String,
              context: ChatContext,
              lastSent: Date?) async -> (reply: String?, rateLimited: Bool, timedOut: Bool, warning: String?, label: String, contextPath: String?, nextSentAt: Date?) {

        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return (nil, false, false, nil, "No context", nil, lastSent)
        }

        if let last = lastSent, Date().timeIntervalSince(last) < config.rateLimitSeconds {
            return (nil, true, false, nil, "No context", nil, lastSent)
        }

        let script = "\(config.repoRoot)/engines/chat_engine/chat_cli.py"
        let clientArg = context.overridePath ?? context.sidecarPath ?? ""
        let result = await runner.run(
            command: [
                config.pythonPath,
                script,
                "--prompt", trimmed,
                "--label", "macos-app",
                "--rate-limit", "\(config.rateLimitSeconds)",
                "--timeout", "\(config.timeoutSeconds)",
                "--context", clientArg
            ],
            workingDirectory: config.repoRoot,
            extraEnv: ["PYTHONPATH": config.repoRoot]
        )

        let nextSent = Date()
        let logLine = """
        chat run:
          prompt: \(trimmed.prefix(120))
          context: \(clientArg.isEmpty ? "(none)" : clientArg)
          exit: \(result.exitCode)
          stdout: \(result.stdout.prefix(400))
          stderr: \(result.stderr.prefix(400))
        -----

        """
        if let data = logLine.data(using: .utf8) {
            let logURL = URL(fileURLWithPath: "/tmp/macos_chat_debug.log")
            if FileManager.default.fileExists(atPath: logURL.path),
               let handle = try? FileHandle(forWritingTo: logURL) {
                _ = try? handle.seekToEnd()
                _ = try? handle.write(contentsOf: data)
                try? handle.close()
            } else {
                try? data.write(to: logURL)
            }
        }

        if result.exitCode != 0 {
            os_log("chat error %{public}@", log: log, type: .error, result.stderr)
            return ("[chat error] \(result.stderr.trimmingCharacters(in: .whitespacesAndNewlines))", false, false, nil, "No context", nil, nextSent)
        }

        guard let data = result.stdout.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return ("[chat error] malformed response", false, false, nil, "No context", nil, nextSent)
        }

        let reply = (json["reply"] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let label = json["label"] as? String ?? "No context"
        let warning = json["warning"] as? String
        let rateLimited = json["rate_limited"] as? Bool ?? false
        let timedOut = json["timed_out"] as? Bool ?? false
        let ctxPath = json["context_path"] as? String
        return (reply, rateLimited, timedOut, warning, label, ctxPath, nextSent)
    }
}
