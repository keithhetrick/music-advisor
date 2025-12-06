# Testing & QA

## Automated

- Full suite: `pytest`
- Spine-only focus: `pytest tools/spine`
- Pytest config: see `pyproject.toml` (`-q`, testpaths=`tests`).

## Manual checks (common)

- After backfill merge: spot-check row counts and a few random rows in `data/spine/backfill/` outputs.
- Coverage sanity: run `python tools/spine/spine_coverage_report_v1.py` and `python tools/spine/report_spine_missing_audio_v1.py`.
- If touching calibration artifacts, ensure new norm files are versioned and referenced consistently.
