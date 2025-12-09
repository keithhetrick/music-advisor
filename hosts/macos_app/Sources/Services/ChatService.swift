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
              lastSent: Date?) async -> (reply: String?, rateLimited: Bool, timedOut: Bool, warning: String?, label: String, nextSentAt: Date?) {

        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return (nil, false, false, nil, "No context", lastSent)
        }

        if let last = lastSent, Date().timeIntervalSince(last) < config.rateLimitSeconds {
            return (nil, true, false, nil, "No context", lastSent)
        }

        let resolution = ChatContextResolver.resolve(selection: context.selection,
                                                     sidecarPath: context.sidecarPath,
                                                     overridePath: context.overridePath,
                                                     historyItems: context.historyItems,
                                                     previewCache: context.previewCache)

        let script = """
import sys
from pathlib import Path
from engines.chat_engine.chat_engine import ChatRequest, run

prompt = sys.argv[1]
client = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
req = ChatRequest(prompt=prompt, context_path=str(client) if client else None, label="macos-app")
res = run(req)
print(res.reply)
"""
        let clientArg = resolution.path ?? ""
        let result = await runner.run(
            command: [config.pythonPath, "-c", script, trimmed, clientArg],
            workingDirectory: config.repoRoot,
            extraEnv: ["PYTHONPATH": config.repoRoot]
        )

        let nextSent = Date()

        let logLine = """
        chat run:
          prompt: \(trimmed.prefix(120))
          context: \(resolution.path ?? "(none)") [label=\(resolution.label)]
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
            return ("[chat error] \(result.stderr.trimmingCharacters(in: .whitespacesAndNewlines))", false, false, resolution.warning, resolution.label, nextSent)
        }

        let reply = result.stdout.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines)
        return (reply, false, false, resolution.warning, resolution.label, nextSent)
    }
}
