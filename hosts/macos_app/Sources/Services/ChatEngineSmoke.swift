import Foundation

/// Optional helper to shell out to the Python chat_engine smoke for e2e validation.
struct ChatEngineSmoke {
    static func run(prompt: String, contextPath: String?) async -> (reply: String?, exit: Int32, stderr: String) {
        let repo = ProcessInfo.processInfo.environment["MA_REPO_ROOT"]
            ?? "/Users/keithhetrick/music-advisor"
        let script = "\(repo)/engines/chat_engine/cli_smoke.py"
        var args = [script, "--prompt", prompt]
        if let ctx = contextPath { args += ["--context", ctx] }
        let runner = RunnerService()
        let result = await runner.run(
            command: ["/usr/bin/python3"] + args,
            workingDirectory: repo,
            extraEnv: ["PYTHONPATH": repo]
        )
        return (result.stdout.isEmpty ? nil : result.stdout, result.exitCode, result.stderr)
    }
}
