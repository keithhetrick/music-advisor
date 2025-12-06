# Music Advisor Probe (JUCE)

An AU/VST3 probe plugin that runs inside a DAW, captures in-situ loudness/peaks, and writes a Music Advisor-compatible JSON sidecar (`juce_probe_features_v1`). Real-time DSP stays allocation-free; sidecar writes happen on a background thread.

## Build (VS Code + CMake + Xcode)

Prereqs: JUCE checkout at `plugins/juce_probe/JUCE` (git submodule or local clone; set `-DJUCE_DIR=/path/to/JUCE` if different).

```bash
cd plugins/juce_probe
./scripts/build_debug.sh        # Configure with Xcode generator + build Debug
# or: ./scripts/build_release.sh
# manual:
# cmake -S . -B build -G Xcode
# cmake --build build --config Debug
```

Artifacts: `build/Debug/Music Advisor Probe.vst3`, `build/Debug/Music Advisor Probe.app` (standalone), `build/Debug/Music Advisor Probe.component` (AU).

## Sidecar output

- Default root: `${MA_DATA_ROOT:-~/music-advisor/data}/features_output/juce_probe/<track_id>/<timestamp>/juce_probe_features.json`
- The UI allows overriding `MA_DATA_ROOT` and setting `track_id` / `session_id`. Host name + sample rate are auto-filled.
- Schema (`juce_probe_features_v1`):

```json
{
  "version": "juce_probe_features_v1",
  "track_id": "my_demo",
  "session_id": "logic_take_1",
  "host": "Logic Pro",
  "sample_rate": 48000.0,
  "generated_at": "2025-01-01T18:30:00Z",
  "build": "0.1.0",
  "features": {
    "global": {
      "duration_sec": 87.5,
      "integrated_rms_db": -14.8,
      "peak_db": -0.6,
      "crest_factor_db": 14.2
    },
    "timeline": [
      { "time_sec": 0.25, "rms_db": -22.1, "peak_db": -8.3 },
      { "time_sec": 0.50, "rms_db": -21.9, "peak_db": -7.9 }
    ]
  }
}
```

## Notes

- Audio thread work is limited to RMS/peak math and a lock-free FIFO push. JSON writes are off the audio thread.
- Capture toggle can be automated; snapshot writes are manual from the UI.
- Uses `MA_DATA_ROOT` if present; otherwise defaults to `~/music-advisor/data`.
