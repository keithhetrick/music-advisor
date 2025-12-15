# Music Advisor Helper UI Guide

## Overview

The helper ships with a “premium” CLI and an optional full-screen TUI to mirror Turbo/NX-style workflows. Rich output is enabled when available and always falls back to plain text for CI/headless runs.

## Quick commands

- `ma palette` — compact command palette.
- `ma test-all [--json]` — runs all tests, shows Rich summary; `--json` emits machine-readable output.
- `ma affected --base origin/main [--json]` — runs only changed projects.
- `ma tasks-run <task> [--cache] [--remote-cache ...]` — Nx-style task runner with cache.
- `ma cache stats|clear|explain --task <name> [--json]` — cache controls and explainability.
- `ma graph [--format ansi|mermaid|dot]` — project/task graph (ANSI + export).
- `ma ui` (coming next) — Textual TUI with split panes (tasks, progress, logs).

## Output modes

- **Rich tables/panels**: used for summaries and status bars when Rich is installed and a TTY is present.
- **JSON**: `--json` on `test-all` / `affected` (and cache commands) emits stable schemas for scripting/CI.
- **Telemetry**: NDJSON to `~/.ma_helper/logs/ma.log` by default; disable with `--no-telemetry` or `MA_HELPER_NO_WRITE=1`.

## Cache

- Local cache lives under `.ma_cache` (configurable). Entries are keyed by project/target + inputs/env/args.
- `ma cache stats` — show entry count and path.
- `ma cache explain --task <name>` — show why a cache entry exists (inputs/outputs/env/args/hash).
- `ma cache clear` — remove cache data.

## Task graph / TUI

- `ma graph` — ANSI graph plus mermaid/dot export for docs/pipelines.
- `ma ui` (Textual) — split-pane dashboard:
  - Left: project tree (select a project to focus its logs).
  - Right: live run table (spinner→✅/❌, cache hit flag) + log tail (filters to the focused project).
  - Keybindings: `/` filter projects (regex, Enter apply, Esc close), `g` graph overlay, `r` rerun-last, `c` cancel (if PID emitted), `?` help, `q` quit.
- Live events are read from `~/.ma_helper/ui_events.ndjson` (override with `MA_UI_EVENTS`). Logs tail `~/.ma_helper/logs/ma.log`. Results fallback: `~/.ma_cache/last_results.json`.

## Live vs. plain

- Live split panes are opt-in (`--live`); defaults stay plain to avoid noise in CI.
- `--no-live` forces plain mode even if Rich is present.

## Tour (breadcrumbs)

- `ma tour` — view progress through suggested steps.
- `ma tour --advance` or running the actual command will auto-advance.
- `ma tour --reset` — start over.

## Assets

Reference inspiration assets live in `docs/assets/cli/` for styling cues; future VHS tapes will be stored in `docs/assets/vhs/` with outputs in `docs/assets/cli/`.
