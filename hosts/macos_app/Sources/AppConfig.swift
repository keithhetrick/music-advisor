import Foundation

struct AppConfig {
    let command: [String]
    let workingDirectory: String?
    let extraEnv: [String: String]

    static func fromEnv() -> AppConfig {
        let env = ProcessInfo.processInfo.environment
        let defaults = defaultPythonFeatures()
        let cmd = env["MA_APP_CMD"]?.split(separator: " ").map(String.init) ?? defaults.command
        let args = env["MA_APP_ARGS"]?.split(separator: " ").map(String.init) ?? defaults.args
        let workingDir = env["MA_APP_WORKDIR"] ?? defaults.workingDirectory

        var extras: [String: String] = defaults.extraEnv
        for (key, value) in env where key.hasPrefix("MA_APP_ENV_") {
            let trimmed = String(key.dropFirst("MA_APP_ENV_".count))
            extras[trimmed] = value
        }

        return AppConfig(command: cmd + args, workingDirectory: workingDir, extraEnv: extras)
    }

    private static func defaultPythonFeatures() -> (command: [String], args: [String], workingDirectory: String?, extraEnv: [String: String]) {
        // Best-effort sensible defaults for Keith’s machine; avoids empty cwd/env.
        let repoRoot = "/Users/keithhetrick/music-advisor"
        let cmd = "/usr/local/bin/python3"
        let script = "\(repoRoot)/engines/audio_engine/tools/cli/ma_audio_features.py"
        let audioPlaceholder = "/Users/keithhetrick/Downloads/lola.mp3"
        let outPlaceholder = "/tmp/ma_features.json"
        let args = [script, "--audio", audioPlaceholder, "--out", outPlaceholder]
        let extraEnv = ["PYTHONPATH": repoRoot]
        return (command: [cmd], args: args, workingDirectory: repoRoot, extraEnv: extraEnv)
    }
}
