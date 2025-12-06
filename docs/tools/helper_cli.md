# Helper CLI (ma.py)

`ma_helper` is a lightweight, Nx/Turborepo-like helper for the monorepo. Code lives under `tools/ma_helper/` with a root wrapper (`python -m ma_helper`) and a console script (`ma`) when installed in editable mode. It wraps `ma_orchestrator` and adds interactive/fuzzy UX, parallelism, graphs, favorites/history, CI planning, and rich summaries. Set an alias for brevity: `alias ma="python -m ma_helper"`.

## Commands

- List projects: `python tools/ma.py list`
- Tasks: `python tools/ma.py tasks [--filter substr] [--json]`
- Test a project: `python tools/ma.py test <project> [--cache off|local|restore-only] [--retries N]`
- Test all: `python tools/ma.py test-all [--parallel N] [--cache off|local|restore-only] [--retries N] [--require-preflight]` (prints a per-project summary table when tests run)
- Affected tests: `python tools/ma.py affected --base origin/main [--parallel N] [--no-diff] [--base-from last] [--since <date/ref>] [--merge-base] [--cache off|local|restore-only] [--retries N] [--require-preflight]`
- Run target: `python tools/ma.py run <project>`
- Deps: `python tools/ma.py deps [--graph mermaid|dot|svg|ansi|text]`
- Map/topology: `ma map --format ansi|mermaid|dot|svg|html [--filter substr] [--open]` (grouped by type, with deps + counts)
- Dashboard: `ma dashboard` (project counts + last run summary + last base) [`--json`|`--html`|`--live`]
- Rich TUI: `ma tui [--interval 1.0] [--duration 60]` (split panels: overview + last results + tips; requires `rich`)
- Preflight: `ma preflight` (checks registry test/run paths exist)
- Interactive picker: `ma select` (fuzzy if prompt_toolkit installed; stays open; Enter/back to return)
- Watch: `ma watch <project> [--cmd \"make test-foo\"] [--preset test|lint] [--rerun-last-failed] [--hotkeys]` (uses `entr` or `watchfiles` fallback; optional hooks `--on-success/--on-fail`; hotkeys r/f/q when watchfiles backend)
- CI plan (no execution): `ma ci-plan --base origin/main [--commands] [--matrix] [--gha|--gitlab|--circle] [--targets test run] [--base-from last] [--since <date/ref>] [--merge-base]`
- GitHub/CI readiness: `ma github-check [--require-clean] [--require-branch main] [--require-upstream] [--preflight] [--verify] [--ci-plan --base origin/main] [--require-optional]` (env overrides: `MA_REQUIRE_CLEAN=1`, `MA_REQUIRE_OPTIONAL=1`)
- Git hook helper: `ma hook pre-push [--install]` (prints or installs a pre-push hook that runs `ma github-check --require-clean --preflight --ci-plan`)
- Pre-commit hook helper: `ma precommit print|install` (pre-commit runs preflight + lint + typecheck)
- Chat dev helper: `ma chat-dev [--log-file logs/chat.log] [--endpoint http://127.0.0.1:8000/chat]` (tmux layout if available; otherwise prints commands to run chat CLI + tail + helper shell)
- Helper self-checks: `python tests/helper/self_check.py` (or `tests/helper/run_helper_tests.sh`) for a quick regression sweep.
- Git helpers: `ma git-branch <project> [--desc d] [--prefix feature] [--upstream origin] [--sparse paths...]`, `ma git-status [--json]`, `ma git-upstream [--remote origin --branch main]`, `ma git-rebase --onto origin/main`, `ma git-pull-check`.
- Registry: `ma registry validate | list | show <project> | add/remove ... | lint [--fix]`
- Info: `ma info <project>` (registry entry + dependents + doc links + suggested watch/smoke)
- Tour: `ma tour` (guided flow; Rich if installed)
- Welcome: `ma welcome` (guided overview + command list)
- Help: `ma help` (command palette style cheat sheet)
- Quickstart: `ma quickstart` (top helper commands to run first)
- Logs: `ma logs [--tail 100]` (tails helper logs)
- Doctor: `ma doctor` (checks venv, git, optional tools) [`--require-optional` to fail if optional deps missing]
- Check: `ma check` (quick sanity: git dirty, venv, watch deps)
- GitHub/CI readiness: `ma github-check [--require-clean] [--require-branch main] [--require-upstream] [--preflight] [--verify] [--ci-plan --base origin/main]`
- Guardrails: `ma guard` (show) / `ma guard --set strict` to require confirmations for risky actions
- Palette: `ma palette` (compact list of common commands)
- Cache controls: `ma cache stats` / `ma cache clean`
- Artifact cache metadata: `ma cache list-artifacts` / `ma cache show-artifact --name audio_engine_test` (stored under `.ma_cache/artifacts/`; written when cache mode is not off and test succeeds)
- Optional deps: `rich` for TUI/live dashboards; `prompt_toolkit` for fuzzy prompts; `tmux` for chat-dev layout (helper falls back to printed commands if tmux fails/unavailable). Git helpers require running inside the git repo (`.git` present).
- Sparse helpers: `ma sparse --set <paths...>` / `--list` / `--reset`
- Scaffold stub: `ma scaffold --type engine|host|shared --name foo [--path ...] [--write-registry]` (creates stub; optionally adds to registry)
- Smokes: `ma smoke pipeline|full|menu` (pipeline → quick_check; full → e2e_app_smoke; menu lists options)
- Lint/type/format: `ma lint`, `ma typecheck`, `ma format` (wrap repo scripts)
- Profiles/presets: `ma profile list|show <name>|apply <name> [--dry-run]` (sparse + playbook presets; e.g. dev/pipeline/minimal)
- Verify gate: `ma verify` (lint + typecheck + smoke pipeline + affected no-diff)
- CI env hints: `ma ci-env`
- REPL: `ma shell` (stay in the helper and run commands interactively)
- Favorites/history:
  - `ma favorites list [--json]`
  - `ma favorites add --name smoke --cmd \"ma affected --base origin/main --parallel 4\"`
  - `ma favorites run --name smoke`
- Rerun last command in history: `ma rerun-last`
- History: `ma history [--limit N]`
- Global dry-run (where supported for shell calls): add `--dry-run` before the command, e.g. `ma --dry-run smoke pipeline`
- Base reuse: `ma affected --base-from last` or `ma ci-plan --base-from last` reuses the last base seen (stored in `~/.ma_helper.json`).
- CI matrix: `ma ci-plan --gha` prints a GitHub Actions matrix snippet; `--matrix` prints the raw matrix JSON.
- Registry hygiene: `ma registry validate` shows missing paths/tests; `ma registry lint --fix` normalizes ordering.
- Caching: `--cache` (off|local|restore-only) skips unchanged projects based on a fast hash of project + test paths (stored in `.ma_cache/cache.json`). Last run summaries live in `.ma_cache/last_results.json`. `--retries N` allows limited retries on failures.
- Artifact metadata is stored under `.ma_cache/artifacts/` when cache mode is not off and tests succeed; use `ma cache list-artifacts`/`show-artifact` to inspect.
- Dashboard exports: `ma dashboard --json|--html` for machine-friendly or shareable output.
- Default preflight enforcement: set `MA_REQUIRE_PREFLIGHT=1` to force preflight on test/test-all/affected/watch/verify.
- Default clean-tree enforcement: set `MA_REQUIRE_CLEAN=1` to require a clean git tree for test/run/watch/affected/verify/ci-plan/github-check.
- Safe run enforcement: set `MA_REQUIRE_SAFE_RUN=1` (or use strict/confirm env) to prompt if a run target is missing.
- State dir override: set `MA_HELPER_HOME` to relocate helper prefs/logs/cache if home is unwritable.

## Live dashboard + tmux split

- Minimal two-terminal setup (no tmux required):
  - Terminal A: `python -m ma_helper shell`
  - Terminal B: `python -m ma_helper dashboard --live --duration 0 --interval 2` (Ctrl-C to stop)
- tmux split (keeps shell + live dash in one window; uses a dedicated socket so it won’t collide with other sessions):
  ```bash
  cd ~/music-advisor && source .venv/bin/activate && \
  tmux -L mahelper new-session -s mahelper 'python -m ma_helper shell' \; \
    split-window -h 'python -m ma_helper dashboard --live --duration 0 --interval 2' \; \
    select-pane -t 0
  ```
- Pane switch: `Ctrl-b` + arrows; detach: `Ctrl-b d`; kill all: `tmux -L mahelper kill-server`.
- If you auto-start tmux in `.zshrc`, guard it to avoid unexpected attaches:
  ```sh
  if [ -z "$TMUX" ]; then
    # tmux attach -t default || tmux new -s default
    :
  fi
  ```
  - Optional config template: `docs/tools/tmux.conf.sample` (copy to `~/.tmux.conf`, then `tmux kill-server` to restart).
  - Handy tmux commands (mahelper socket):
    - List sessions: `tmux -L mahelper ls` (errors if none, that is fine)
    - Kill helper server: `tmux -L mahelper kill-server`
    - Kill one session: `tmux -L mahelper kill-session -t mahelper`
    - Reattach: `tmux -L mahelper attach -t mahelper`
    - Pane switch: `Ctrl-b` + arrows; show numbers: `Ctrl-b q` then number
    - Detach: `Ctrl-b d`; close pane: `Ctrl-b x`
  - Completions: `ma completion zsh` or `ma completion bash` prints a completion script; source it in your shell (e.g., `eval "$(python -m ma_helper completion zsh)"`) for helper command completion.

## Optional extras

- Fuzzy/select: `pip install prompt_toolkit`
- Watch fallback: `pip install watchfiles` (if `entr` is not installed)
- SVG graph output: install `graphviz` (`dot` on PATH)

## Notes

- Parallel flags fan out per-project tests using threads; pick a sensible `--parallel` for your machine.
- `ci-plan` prints JSON of affected projects; use it in CI to decide which jobs to run.
- Favorites/history/theme/last-base/last-failed and helper logs/cache live under `MA_HELPER_HOME` (default `~/.ma_helper`; falls back to `/tmp/ma_helper` if needed). Optional deps: `rich` for TUI/live dashboards; `prompt_toolkit` for fuzzy prompts; `tmux` for chat-dev layout (helper falls back to printed commands if tmux fails/unavailable). Git helpers require running inside the git repo (`.git` present).***
