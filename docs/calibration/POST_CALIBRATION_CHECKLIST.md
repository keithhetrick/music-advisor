# Post-Calibration / Spine Refresh Checklist (Client-Only)

- **Update calibration tags**: set `HCI_CAL_VERSION`/`HCI_CAL_DATE` defaults if the calibration file changes (appears in rich text headers).
- **Run tests**: `pytest` (root project). Vendor: `cd vendor/MusicAdvisor_BuilderPack && source .venv/bin/activate && pytest builder/export/MusicAdvisor -q` (host-dependent tests stay ignored unless engine is installed).
- **Run smokes**:
  - `scripts/smoke_full_chain.sh /path/to/audio.wav` (client helpers only)
  - `./automator.sh /path/to/audio.wav` (emits client helpers)
- **Optional benchmark sweep**: run a small, stable set of reference tracks through the local pipeline and spot-check HCI_v1 ranges to catch drift.
- **Artifacts**: ensure only `.client.*` helpers are emitted; delete/ignore any legacy helper files using the old token.
- **Docs/help**: refresh any calibration/version mentions in user-facing text if version/date changed.
