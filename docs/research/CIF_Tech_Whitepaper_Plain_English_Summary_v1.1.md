# CIF Music Advisor (HCI) — Plain-English Overview

Version v1.1 · 2025-11-02 · © 2025 Bellweather Studios / Keith Hetrick

## What it is

The Creative Intelligence Framework (CIF) turns the patterns of hit songs into a practical **decision aid**. It outputs a single number—the **Hit Confidence Index (HCI)** from 0–1—summarizing how “release-ready” a track is for a given market.

## How it works (no math required)

CIF listens to the song, extracts measurable traits (tempo, loudness, structure, energy, etc.), and scores **six areas**. We take an **equal-weight average** of those six to get HCI. You also get per-axis feedback showing _why_ the score is what it is and where to improve.

> Where this lives in the repo: feature extraction = `tools/cli/ma_audio_features.py` (see `docs/pipeline/README_ma_audio_features.md`), axes/echo = `docs/hci/hci_spec.md`, norms = `docs/norms/market_norms.md`, host presentation = `docs/host_chat/frontend_contracts.md`.

### The six axes in plain language

- **Historical** — Echoes proven song archetypes without sounding copy-paste.
- **Cultural** — Near the current zeitgeist: peer adjacency, format momentum, regional reach.
- **Market** — Fits today’s format norms (tempo, LUFS, time-to-chorus, duration, energy, danceability).
- **Emotional** — Energy/valence curve lands where hits land, with a satisfying chorus lift.
- **Sonic** — Mix/master quality and rhythmic bed suitability for the target lane.
- **Creative** — Expert craft signal: hook economy, title alignment, structural efficiency. (Lyrics partially proxied today; becomes lyric-aware via Luminaire.)

## What lyric support is coming (Luminaire)

**Luminaire** adds:

- **HLM (Historical Lyric Model)** — maps lyric archetypes (confessional minimal, empowerment disco, storyfolk, etc.).
- **HLI (Hit Lyric Index)** — scores lyric “hit-ness”: repetition density, sentiment lift verse→chorus, rhyme density, title prominence, novelty vs. archetype.

**Integration path:** initially HLI informs **Creative** and **Cultural** axes; then it can become a **seventh axis** that contributes directly to HCI.

## How to read HCI

- **0.80+** — exceptional
- **0.75–0.79** — release-ready hit lane
- **0.70–0.74** — strong (light tweaks)
- **0.60–0.69** — good; lane clarity needed
- **0.50–0.59** — work-in-progress
- **<0.50** — niche/experimental for mass market

> HCI isn’t a guarantee—it surfaces **specific levers** (e.g., LUFS, TTC, chorus lift) so you can adjust _before_ release.

## Typical workflows

- **A&R greenlight:** sanity-check a short list; pick the strongest single for the target format.
- **Pre-mix optimization:** raise chorus lift; align LUFS and energy to lane targets.
- **Writer-room iteration:** compare versions; keep the one that climbs on the weak axis.
- **Post-release debrief:** backtest outcomes; refine profiles and creative rubrics.

## Governance & inputs

- Audio features can be extracted locally via **Automator** (no audio leaves the machine in local mode).
- Cultural inputs can be curated or evaluator-proxied; lyrics are **licensed/creator-provided** when used.
- Methods are documented in the technical whitepaper; weights/archetypes are proprietary but **auditable at the axis level**.

## Ownership & IP (short)

© 2025 **Bellweather Studios / Keith Hetrick**. Proprietary: taxonomy, normalization design, archetype construction, market-tier calibration. Generic: code languages, standard DSP/NLP primitives, public standards.

## Contact

Bellweather Studios / Keith Hetrick — via existing partner channels.
