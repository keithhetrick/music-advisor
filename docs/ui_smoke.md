UI Smoke Checklist (manual)
===========================

1) Launch app
   - `cd hosts/macos_app && ./scripts/swift_run_local.sh`

2) Chat flow
   - In Console tab: select History or Last run context.
   - Send a prompt; confirm badges update and toast slides/fades.
   - Try manual path in prompt (paste a `.client.rich.txt`) and verify toast warning/info.

3) Run flow
   - Drop an audio file in Run tab; run defaults; reveal/preview sidecar.
   - Confirm chat context switches to last run when available.

4) Snippets
   - Use a snippet chip; prompt pre-fills and focuses.

5) Rails/toggles
   - Hide/show rail; ensure Run/History/Chat labels don’t clip; toggle feels subtle.

6) Toasts
   - Trigger any toast (e.g., missing file) and verify left-slide + progress bar + auto-dismiss timing.

7) Pipeline smoke (optional)
   - `./scripts/pipeline_smoke.sh /path/to/audio.wav /tmp/ma_features_smoke.json`
   - Confirm JSON is written.
