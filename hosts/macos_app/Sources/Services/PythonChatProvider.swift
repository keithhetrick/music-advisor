import Foundation

actor PythonChatProvider: ChatProvider {
    private let runner = RunnerService()
    private let config: ChatProviderConfig

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
from tools.chat.chat_router import route_message
from tools.chat.chat_context import ChatSession

prompt = sys.argv[1]
client = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
sess = ChatSession(session_id="macos-app")
reply = route_message(sess, prompt, client_path=client)
print(reply)
"""
        let clientArg = resolution.path ?? ""
        let result = await runner.run(
            command: [config.pythonPath, "-c", script, trimmed, clientArg],
            workingDirectory: config.repoRoot,
            extraEnv: ["PYTHONPATH": config.repoRoot]
        )

        let nextSent = Date()

        if result.exitCode != 0 {
            return ("[chat error] \(result.stderr.trimmingCharacters(in: .whitespacesAndNewlines))", false, false, resolution.warning, resolution.label, nextSent)
        }

        let reply = result.stdout.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines)
        return (reply, false, false, resolution.warning, resolution.label, nextSent)
    }
}
