# Python compatibility notes

Status: captured from pytest warnings during `python -m ma_helper test-all` (Py 3.11.2).

- Deprecations targeting Python 3.13: `aifc`, `audioop`, `sunau` via `audioread.rawread` (pulled in by librosa fallback). Action: validate upgrades to libraries that drop these deps or switch loaders before bumping to 3.13.
- Librosa warning: `librosa.core.audio.__audioread_load` is deprecated (0.10 → removal in 1.0) when audioread is used as a fallback. Action: prefer soundfile path where possible or bump librosa once a migration path is ready.
- Runtime warning: `PySoundFile failed. Trying audioread instead.` (expected when soundfile cannot open a file). Action: nothing immediate; ensure test fixtures remain readable by soundfile to avoid extra fallbacks.

Suggested follow-ups:

- Dry-run on Python 3.12/3.13 pre-release to surface any breaking removals early.
- If noise becomes distracting in CI, add targeted warning filters with comments pointing back to this file.
