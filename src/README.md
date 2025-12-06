# src/ namespace

This namespace exists to keep legacy imports working while we migrate into the
`engines/` / `hosts/` / `shared/` layout.

- `policies/` and any other helper modules live here to avoid sprinkling
  `sys.path` hacks across tooling.
- Legacy compatibility packages (`ma_audiotools/`, `music-advisor/`,
  `ma_ttc_engine/`, `host/`, `lyrics/`) have been archived under
  `archive/legacy_src/`. Use `ma_audio_engine.*` (and other engine/host/shared
  packages) directly; venv console scripts now point at these canonical modules.

New code should import from `ma_audio_engine.*` (or other engine/host/shared
packages) directly. Leave this folder in place until external callers have
fully migrated.
