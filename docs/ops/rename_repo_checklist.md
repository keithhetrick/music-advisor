# Repo Rename Checklist (music-advisor)

Use this when renaming the local folder and aligning paths.

Steps

1. Move/clone the folder (local only):
   mv ~/music-advisor ~/music-advisor
2. Set REPO (optional but recommended):
   export REPO=~/music-advisor
3. Recreate the venv (shebangs embed the old path):
   cd ~/music-advisor
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.lock
4. Update Automator/Quick Action path:
   - Point to $HOME/music-advisor/automator.sh "$@"
   - Or use $REPO/automator.sh if REPO is exported.
5. Sanity check:
   - Run: make quick-check (or infra/scripts/quick_check.sh)
   - Drag-and-drop one file through Automator; confirm 12-file payload.

Notes

- Scripts/configs now use ${REPO:-$HOME/MusicAdvisor} defaults, so folder name changes won’t break paths.
- Remote repo name (e.g., music-advisor) is independent of the local folder name; update Git remote only if you rename the remote.
