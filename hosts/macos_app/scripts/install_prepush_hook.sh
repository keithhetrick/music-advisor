#!/usr/bin/env zsh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname "$0")/../.." && pwd)"
HOOK="$REPO_ROOT/.git/hooks/pre-push"
SCRIPT_REL="hosts/macos_app/scripts/prepush_smoke.sh"

cat > "$HOOK" <<'HOOK'
#!/usr/bin/env zsh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
"$REPO_ROOT/hosts/macos_app/scripts/prepush_smoke.sh"
HOOK

chmod +x "$HOOK"
echo "Installed pre-push hook to run $SCRIPT_REL"
