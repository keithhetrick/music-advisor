# Troubleshooting

Common issues and quick fixes.

## Environment / install

- **Missing deps / wheels**: Ensure venv is active. Run `pip install -r requirements.txt` and `pip install -r requirements.lock || true`.
- **FFmpeg not found**: Install via Homebrew (`brew install ffmpeg`) or your package manager.
- **Librosa / audioread warnings**: Expected when PySoundFile can’t open some formats; it falls back to audioread. OK to ignore unless extraction fails.

## Paths & data

- **Hardcoded path errors**: Use `MA_DATA_ROOT` to override data location. Artifacts write under `data/features_output/...` by default.
- **Bootstrap failing**: Check `infra/scripts/data_manifest.json` URLs and SHA256 placeholders. Ensure no credentials/presigned URLs are in the manifest.
- **Permissions**: If Quick Action/Automator fails, confirm the script points to `${REPO:-$HOME/music-advisor}/automator.sh` and your venv is set up.
- **Logs location**: Check `logs/automator_*.log` for Automator runs; check `logs/` for pipeline-driver logs if enabled.

## Pipeline/runtime

- **Sidecar/tempo/key failures**: Rerun with `--no-cache` or `--force` if configs changed. Ensure tempo/key sidecar DBs exist under `data/public` (or MA_DATA_ROOT override).
- **Cache issues**: `make clean` to clear caches; `make deep-clean` for a full reset (prompts).
- **Tests slow**: Use `infra/scripts/test_affected.sh` for scoped runs; use `make quick-check` before commits/tags.
- **macOS Automator quirks**: Ensure Automator/Quick Action shell script uses `${REPO:-$HOME/music-advisor}/automator.sh "$@"` and that the workflow has permission to access Files/Folders (System Settings → Privacy & Security → Full Disk Access if needed).
