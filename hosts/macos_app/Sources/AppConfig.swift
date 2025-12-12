import Foundation

struct AppConfig {
    let command: [String]
    let workingDirectory: String?
    let extraEnv: [String: String]
    let profiles: [Profile]

    struct Profile {
        let name: String
        let command: [String]
        let workingDirectory: String?
        let extraEnv: [String: String]
        let outputPath: String?
    }

    static func fromEnv() -> AppConfig {
        var env = ProcessInfo.processInfo.environment
        let fileEnv = loadEnvFile(using: env)
        for (k, v) in fileEnv where env[k] == nil {
            env[k] = v
        }
        let jsonCfg = loadJSONConfig(using: env)

        let defaults = defaultPythonFeatures(env: env, config: jsonCfg)
        let cmd = env["MA_APP_CMD"]?.split(separator: " ").map(String.init) ?? defaults.command
        let args = env["MA_APP_ARGS"]?.split(separator: " ").map(String.init) ?? defaults.args
        let workingDir = env["MA_APP_WORKDIR"] ?? defaults.workingDirectory

        var extras: [String: String] = defaults.extraEnv
        for (key, value) in env where key.hasPrefix("MA_APP_ENV_") {
            let trimmed = String(key.dropFirst("MA_APP_ENV_".count))
            extras[trimmed] = value
        }

        let profiles = buildProfiles(from: jsonCfg, env: env)

        return AppConfig(command: cmd + args, workingDirectory: workingDir, extraEnv: extras, profiles: profiles)
    }

    private static func defaultPythonFeatures(env: [String: String], config: [String: Any]) -> (command: [String], args: [String], workingDirectory: String?, extraEnv: [String: String]) {
        // Best-effort sensible defaults; expand ~ and fall back to the current user's HOME.
        let home = env["HOME"] ?? NSHomeDirectory()
        let repoRootRaw = env["MA_APP_DEFAULT_WORKDIR"]
            ?? config["default_workdir"] as? String
            ?? "\(home)/music-advisor"
        let repoRoot = expandTilde(repoRootRaw, home: home)

        // Default to the real pipeline entrypoint (Automator shim).
        let cmdRaw = env["MA_APP_DEFAULT_CMD"]
            ?? config["default_cmd"] as? String
            ?? "\(repoRoot)/automator.sh"
        let cmd = expandTilde(cmdRaw, home: home)

        let audioPlaceholder = env["MA_APP_DEFAULT_AUDIO"]
            ?? config["default_audio"] as? String
        let expandedAudio = audioPlaceholder.map { expandTilde($0, home: home) }

        let argsFromConfig = config["default_args"] as? [String]
        let args = env["MA_APP_DEFAULT_ARGS"]?
            .split(separator: " ")
            .map(String.init)
            ?? argsFromConfig
            ?? (expandedAudio.map { [$0] } ?? [])

        var extraEnv: [String: String] = [
            // Keep REPO available for the pipeline script.
            "REPO": repoRoot
        ]
        if let pythonPathRaw = env["MA_APP_ENV_PYTHONPATH"]
            ?? (config["env"] as? [String: String])?["PYTHONPATH"] {
            extraEnv["PYTHONPATH"] = expandTilde(pythonPathRaw, home: home)
        }
        if let envDict = config["env"] as? [String: String] {
            for (k, v) in envDict where extraEnv[k] == nil {
                extraEnv[k] = expandTilde(v, home: home)
            }
        }
        return (command: [cmd], args: args, workingDirectory: repoRoot, extraEnv: extraEnv)
    }

    private static func expandTilde(_ path: String, home: String) -> String {
        guard path.hasPrefix("~") else { return path }
        if path == "~" { return home }
        if path.hasPrefix("~/") {
            let suffix = path.dropFirst(2)
            return "\(home)/\(suffix)"
        }
        return path
    }

    private static func loadEnvFile(using env: [String: String]) -> [String: String] {
        let defaultPath = "/Users/keithhetrick/music-advisor/hosts/macos_app/.env.local"
        let path = env["MA_APP_ENV_FILE"] ?? defaultPath
        guard let content = try? String(contentsOfFile: path) else { return [:] }
        var result: [String: String] = [:]
        for line in content.split(separator: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.isEmpty || trimmed.hasPrefix("#") { continue }
            guard let eq = trimmed.firstIndex(of: "=") else { continue }
            let key = String(trimmed[..<eq]).trimmingCharacters(in: .whitespaces)
            let value = String(trimmed[trimmed.index(after: eq)...]).trimmingCharacters(in: .whitespaces)
            if !key.isEmpty {
                result[key] = value
            }
        }
        return result
    }

    private static func loadJSONConfig(using env: [String: String]) -> [String: Any] {
        let defaultPath = "/Users/keithhetrick/music-advisor/hosts/macos_app/config/defaults.json"
        let path = env["MA_APP_CONFIG_FILE"] ?? defaultPath
        guard
            let data = try? Data(contentsOf: URL(fileURLWithPath: path)),
            let obj = try? JSONSerialization.jsonObject(with: data, options: []),
            let dict = obj as? [String: Any]
        else { return [:] }
        return dict
    }

    private static func buildProfiles(from config: [String: Any], env: [String: String]) -> [Profile] {
        guard let profilesDict = config["profiles"] as? [String: Any] else { return [] }
        var profiles: [Profile] = []
        for (name, raw) in profilesDict {
            guard let dict = raw as? [String: Any] else { continue }
            let cmd = (dict["cmd"] as? [String]) ?? []
            let args = (dict["args"] as? [String]) ?? []
            let workdir = dict["workdir"] as? String
            let envDict = dict["env"] as? [String: String] ?? [:]
            let output = dict["out"] as? String
            profiles.append(Profile(name: name, command: cmd + args, workingDirectory: workdir, extraEnv: envDict, outputPath: output))
        }
        return profiles.sorted { $0.name < $1.name }
    }
}
