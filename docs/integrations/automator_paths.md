# Automator / macOS Quick Actions (repo path dependency)

The macOS Automator/Quick Action wrappers (drag-and-drop, Quick Action) call this repo’s `automator.sh` and related scripts. If you move or clone the repo to a new path (including an external drive), update the Automator actions to point at the new location.

Key paths:

- `automator.sh` (root): entrypoint for drag-and-drop/Quick Action.
- `infra/scripts/data_bootstrap.py` (data fetch if you choose to run it).
- `infra/scripts/quick_check.sh` (smoke).

How to update after moving the repo:

1. Note the new repo path (e.g., `/Volumes/ExtDisk/music-advisor`).
2. Open your Automator/Quick Action workflow and edit the shell action to point to the new `automator.sh` path.
3. Re-run a drag-and-drop smoke to confirm the 12-file payload under `data/features_output/...`.

If you need to relocate data/calibration to another drive, set env vars in the Automator shell action:

- `MA_DATA_ROOT=/path/on/drive/data`
- `MA_CALIBRATION_ROOT=/path/on/drive/calibration`

These env vars are honored globally via `ma_config` path helpers; all components will use the new roots.

## Automator shell snippet (single line)

The Automator “Run Shell Script” action can be a single line pointing at this repo:

```bash
REPO="${REPO:-$HOME/music-advisor_current}"
"$REPO/automator.sh" "$@"
```

Recommended: point a stable symlink to your checkout and update it when you move/rename the repo:

```bash
ln -sfn /path/to/music-advisor ~/music-advisor_current
```

Add env vars inline if you want custom roots:

```bash
MA_DATA_ROOT=/Volumes/ExtDisk/ma-data \
MA_CALIBRATION_ROOT=/Volumes/ExtDisk/ma-calib \
REPO="${REPO:-$HOME/music-advisor_current}" \
"$REPO/automator.sh" "$@"
```
