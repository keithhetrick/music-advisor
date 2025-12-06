"""
Pipeline defaults for Automator/Quick Action flows.

These values seed the environment for ``tools/pipeline_driver.py`` and related
wrappers; callers may override via:
- env: ``HCI_BUILDER_PROFILE``, ``NEIGHBORS_PROFILE``, ``SIDECAR_TIMEOUT_SECONDS``
- JSON: driver flag ``--config <path>`` with keys matching the constants below
- CLI flags: where exposed by wrappers (e.g., Automator env overlays)

Purpose:
- Keep profile/timeout choices centralized and reproducible.
- Allow UI wrappers and Automator to swap profiles/timeouts without code edits.

Notes:
- Side effects: none (constants only). If you add new knobs, update docs (`docs/pipeline/PIPELINE_DRIVER.md`, `docs/DEBUGGING.md`) and tests if applicable.
"""
from __future__ import annotations

# Default profiles; override via env HCI_BUILDER_PROFILE / NEIGHBORS_PROFILE
HCI_BUILDER_PROFILE_DEFAULT = "hci_v1_us_pop"
NEIGHBORS_PROFILE_DEFAULT = "echo_neighbors_us_pop"

# Default sidecar timeout (seconds); override via env SIDECAR_TIMEOUT_SECONDS - default 5 minutes
SIDECAR_TIMEOUT_DEFAULT = 300
