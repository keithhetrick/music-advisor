# Packaging the MusicAdvisor Stack into a macOS App

This guide captures an offline‑first, single‑app packaging strategy that keeps the host/chat + recommendation engine functional on-device, while allowing optional connected features.

## 1) What ships in the app bundle

- Embedded Python runtime (via PyInstaller/briefcase or similar), containing:
  - `advisor_host` (chat/orchestration, intents, tutorials)
  - `recommendation_engine` (rec/advisory logic)
  - Baseline configs: `config/intents.yml`, host profiles, tutorials, reply schema.
  - Baseline market norms snapshot (small JSON; e.g., a recent Hot100/Top40 slice) and any minimal advisor defaults.
- Native deps (ffmpeg, numpy) prebuilt once if needed by your pipeline.
- No external services required for core advisory/rec flows.

## 2) Data & state locations

- Read-only assets in the app bundle: configs, baseline norms snapshot, tutorials.
- Writable state under `~/Library/Application Support/<AppName>/`:
  - Session store: in-memory by default; optional tiny SQLite file for persistence.
  - Logs/metrics: JSONL logs with rotation/size caps.
  - Optional downloaded data (updated norms/configs) with version tags; evictable cache.

## 3) Offline vs connected modes

- Offline mode (default):
  - Uses bundled norms snapshot and advisory logic.
  - No network calls; health/readiness endpoints can be disabled or bound to 127.0.0.1 for debug.
- Connected mode (opt-in):
  - Allows “Refresh norms/config” action to pull updated snapshots.
  - Optional external stores (Redis/Postgres) or metrics exporters (Prom/OTEL) via feature flags/env.
  - Auth/token required for any external calls.

## 4) Size & resource controls

- Cap session history length/bytes; cap log/metrics files and rotate.
- Cap request size in the local HTTP stub; enforce per-session/IP rate limits even in-app to avoid runaway loops.
- Gate any large datasets behind “download on demand” with eviction.

## 5) Security & privacy

- Sanitize user strings (strip HTML/ANSI; optional profanity filter).
- If exposing local HTTP, bind to 127.0.0.1; optionally require a simple bearer token in connected mode.
- No external calls unless the user opts in and provides credentials.

## 6) Config & extensibility

- Keep tunables as small text assets (YAML/JSON) for intents/profiles/thresholds; validate on load.
- Allow hot-reload from disk in dev/debug builds; lock configs for App Store builds.
- Maintain strict schema checks on inbound/outbound messages.

## 7) Observability

- File-based JSONL logs under App Support; optional metrics exporter behind a flag.
- Health/readiness endpoints: liveness + dependency checks (session store, norms availability). Disable or bind locally in production builds unless needed.

## 8) Build targets

- Single binary with two modes:
  - Offline-first (default settings, bundled norms, no external deps).
  - Connected (same binary, but enables refreshers/store/metrics when flags/credentials are present).
- Build scripts should bundle assets, embed version metadata for norms/configs, and set default paths for logs/state under App Support.

## 9) Recommended defaults

- Session store: in-memory with optional file/SQLite persistence; TTL and size caps.
- Norms: ship one recent snapshot; expose “update data” action in connected mode.
- Logs: rotate at modest size (e.g., 5–10 MB) with a small retention count.
- History: max 50 turns and/or byte cap.

## 10) Asset packing helper

- Use `python -m advisor_host.cli.pack_macos_assets --out build/macos_bundle_assets [--baseline-norms path]` to gather configs/schemas and optional baseline norms into a staging folder.

This keeps the app self-contained, small, and functional offline, with clear hooks to enable richer backends when running in an environment that allows it.
