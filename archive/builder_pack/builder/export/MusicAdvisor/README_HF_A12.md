# HF-A12 — Back-to-Normal Patch

Purpose: restore spec-correct scoring by centralizing HCI at Host (cap=0.58),
gating TTC at conf≥0.60 (else TTC=NA and drop chorus-lift), and isolating
advisory systems from KPI paths. Includes run-card emission + tests.

How to integrate:

Install once (outer env):
```bash
pip install --no-build-isolation -e vendor/MusicAdvisor_BuilderPack/builder/export/MusicAdvisor
```

1. Import and use `music_advisor.host.policy.Policy` to configure caps/gates.
2. Compute KPI only via `music_advisor.host.kpi.hci_v1(audio_axes, policy)`.
3. In your audio pipeline, call
   `apply_ttc_gate_and_lift(...)` (segmentation) after you compute TTC & spans.
4. Emit run-cards per track with `run_card.emit_run_card(...)`.
5. Run tests: `pytest -q`.

This patch is additive; wire calls into your existing pipeline where noted.
