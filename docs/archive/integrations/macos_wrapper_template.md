# macOS Wrapper Template (local-only)

Goal: wrap CLI/Automator flows without leaking secrets or paths.

Key practices

- Store any tokens/keys in Keychain; never flat files. Example (Terminal):
  `security add-generic-password -a "$USER" -s "musicadvisor.api_token" -w "VALUE"`
- Constrain file access: only operate on user-selected files/folders; validate paths under repo/ingest roots.
- Logging: set `LOG_REDACT=1 LOG_SANDBOX=1` before invoking CLI; avoid logging full user paths in the wrapper.
- Temps: create under `$TMPDIR` with cleanup after run; avoid world-writable dirs.

Swift pseudo-template

```swift
import AppKit
let panel = NSOpenPanel()
panel.allowsMultipleSelection = true
panel.canChooseDirectories = false
if panel.runModal() == .OK {
  let paths = panel.urls.map { $0.path }
  let task = Process()
  task.environment = [
    "LOG_REDACT": "1",
    "LOG_SANDBOX": "1",
    "PYTHONPATH": "/path/to/repo:/path/to/repo/src"
  ]
  task.launchPath = "/bin/zsh"
  task.arguments = ["-c", "/path/to/repo/scripts/automator.sh \"\(paths.joined(separator: \"\"\"\" \"\"\"\"))\""]
  try? task.run()
}
```

AppleScript/Automator shell template

```bash
#!/bin/zsh
export LOG_REDACT=1
export LOG_SANDBOX=1
export PYTHONPATH="$HOME/music-advisor:$HOME/music-advisor/src:$PYTHONPATH"
REPO="$HOME/music-advisor"
SCRIPT="$REPO/automator.sh"
for f in "$@"; do
  "$SCRIPT" "$f"
done
```

Permissions

- Avoid `sudo`; run as the invoking user.
- Ensure the wrapper binary/script is not world-writable.

Cleanup

- Trap and remove any temp dirs you create; do not leave intermediates with user data.
