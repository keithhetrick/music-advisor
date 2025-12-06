# macOS Integrations (Offline-First)

How to run, wrap, and package the pipeline/host on macOS without losing context or safety. Merges the Automator quickstart, wrapper template, and app-packaging guidance.

## 1) Automator / Quick Action / CLI

- **Default flow:** Automator + drag-and-drop call `tools/pipeline_driver.py --mode hci-only --extras` via `automator.sh`.
- **Outputs:** 12-file set in `features_output/YYYY/MM/<stem>/`: `*.features.json`, `*.sidecar.json`, `*.merged.json`, `.client.txt/.json/.rich.txt`, `.hci.json`, `.neighbors.json`, `run_summary.json`. Logs in `logs/automator_*.log` (Automator) and `logs/pipeline_*.log` (engine/full).
- **Full pipeline:** use `tools/pipeline_driver.py --mode full --extras --audio <file> --out-dir <dir>` (or set `PIPELINE_DRIVER` in Automator/macOS app) to add `<ts>.pack.json` + `engine_audit.json`.
- **Repo path dependency:** if you move/clone the repo (e.g., external drive), update Automator/Quick Action to point at the new `automator.sh` path. For data/calibration relocation, set `MA_DATA_ROOT`/`MA_CALIBRATION_ROOT` in the Automator shell action; `ma_config` respects these globally.
- **Best practice:** point a stable symlink (e.g., `~/music-advisor_current`) at your checkout and call `"$HOME/music-advisor_current/automator.sh" "$@"` in Automator. Update the symlink if you move/rename the repo; Automator stays unchanged.
- **Config:** defaults in `ma_config/pipeline.py`; override via env or `--config <json>` (profiles/timeouts). Sidecar preflight runs `scripts/check_sidecar_deps.sh` under the repo venv.
- **Dev flags:** `--skip-hci-builder` to skip HCI/client.rich/neighbors; `--skip-neighbors` sets `SKIP_CLIENT=1` in builder for faster runs.
- **Env toggles:** `ECHO_TIERS`, `SKIP_CLIENT`, `HCI_BUILDER_PROFILE`, `NEIGHBORS_PROFILE`, `SIDECAR_TIMEOUT_SECONDS`, `LOG_REDACT`, `LOG_SANDBOX`, `ALLOW_CUSTOM_SIDECAR_CMD`.

## 2) Wrapper patterns (local-only)

- **Principles:** no secrets in files (use Keychain), constrain file access to user-selected paths, enable redaction/sandbox logs, clean up temp files.
- **AppleScript/Automator shell template:**

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

- **Swift pseudo-template:** uses `NSOpenPanel` for file selection, sets `LOG_REDACT/LOG_SANDBOX/PYTHONPATH`, and invokes `automator.sh` via `/bin/zsh`.
- **Permissions:** avoid `sudo`; wrapper binaries/scripts should not be world-writable. Keep temp dirs under `$TMPDIR` and clean them up.

## 3) Packaging into a macOS app (offline-first)

- **What ships:** embedded Python runtime (PyInstaller/briefcase or similar) containing `advisor_host` (chat) + `recommendation_engine`; configs (`config/intents.yml`, host profiles, tutorials, reply schema); a small bundled market norms snapshot; optional native deps (ffmpeg, numpy) prebuilt once.
- **Data/state:** read-only assets in app bundle; writable under `~/Library/Application Support/<AppName>/` for sessions, logs/metrics, optional downloaded norms/configs (versioned, evictable).
- **Offline vs connected:** offline default uses bundled snapshot and no network. Connected mode (opt-in) can refresh norms/configs and enable external stores/metrics with credentials.
- **Security:** bind any local HTTP to 127.0.0.1; optional bearer token for connected mode; sanitize user strings; enable redaction/sandbox logging.
- **Resource controls:** cap session history, request sizes, and log file rotation; gate large downloads behind “download on demand.”
- **Config/extensibility:** keep tunables as YAML/JSON assets; validate on load; allow hot-reload in dev builds, lock for App Store builds; maintain strict schemas on I/O.
- **Observability:** JSONL logs with correlation IDs; optional metrics exporter; health/readiness endpoints for liveness/deps (disable or local-only in production builds).
- **Build modes:** single binary with offline-first defaults; connected mode enabled by flags/creds for refreshers/stores/metrics.

### Suggested app layout (bundle)

- `Contents/Resources/config/` — intents/profile/tutorial YAML, norms snapshot JSON.
- `Contents/Resources/bin/` — embedded Python + wheels (ffmpeg/essentia if bundled).
- `Contents/MacOS/<AppBinary>` — launcher that sets env (`PYTHONPATH`, `LOG_REDACT`, `LOG_SANDBOX`, `HOST_PORT=127.0.0.1:<port>`) and invokes host.
- App Support (`~/Library/Application Support/<AppName>/`) — sessions, logs, optional downloaded norms/configs; rotate/size-cap logs here.

## 4) Troubleshooting (macOS)

- No log: ensure Automator points to this repo’s `automator.sh`; check `logs/automator_*.log`.
- Slow Finder refresh: tail the log to confirm progress.
- Missing venv: create/activate `.venv` and install deps (`pip install -r requirements.txt`).
- Sidecar missing: run `scripts/check_sidecar_deps.sh`; use `--require-sidecar` to fail instead of fallback.
