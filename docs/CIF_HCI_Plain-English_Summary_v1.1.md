# CIF Music Advisor (HCI) — Plain‑English Overview

_Version v1.1 · 2025‑11‑02 · © 2025 Bellweather Studios / Keith Hetrick_

## What it is

The Creative Intelligence Framework (CIF) turns the patterns of hit songs into a practical **decision aid**. It outputs a single number, the **Hit Confidence Index (HCI)** from 0–1, summarizing how “release‑ready” a track is for a given market.

## How it works (no math required)

CIF listens to the song, extracts measurable traits (tempo, loudness, structure, energy, etc.), and scores **six areas**. We take an **equal‑weight average** of those six to get HCI. You also get per‑axis feedback showing _why_ the score is what it is and where to improve.

### The six axes in plain language

- **Historical** — Does it echo proven song archetypes without sounding copy‑paste?
- **Cultural** — Is it near the current zeitgeist: peer adjacency, format momentum, regional reach?
- **Market** — Does it fit today’s radio/playlist format norms (tempo, LUFS, time‑to‑chorus, duration, energy, danceability)?
- **Emotional** — Does the energy/valence curve land where hits typically land, with a satisfying chorus lift?
- **Sonic** — Mix/master quality and rhythmic bed suitability for the target lane.
- **Creative** — Expert craft signal: hook economy, title alignment, structural efficiency. (Lyrics partially proxied today; becomes lyric‑aware via Luminaire.)

## What lyric support is coming (Luminaire)

**Luminaire** adds two pieces:

- **HLM (Historical Lyric Model)** maps lyric archetypes (confessional minimal, empowerment disco, storyfolk, etc.).
- **HLI (Hit Lyric Index)** scores lyric “hit‑ness”: repetition density, sentiment lift verse→chorus, rhyme density, title prominence, novelty vs. archetype.

**Integration path:** initially HLI informs the **Creative** and **Cultural** axes. Next, it can become a **seventh axis** so lyrics contribute directly to the composite.

## How to read HCI

- **0.80+** — exceptional
- **0.75–0.79** — release‑ready hit lane
- **0.70–0.74** — strong (light tweaks)
- **0.60–0.69** — good; lane clarity needed
- **0.50–0.59** — work‑in‑progress
- **<0.50** — niche/experimental for mass market

> The score is not a guarantee. It surfaces **specific levers** (e.g., LUFS, TTC, chorus lift) so you can adjust _before_ release.

## Typical workflows

- **A&R greenlight:** sanity‑check a short list; pick the strongest single for the target format.
- **Pre‑mix optimization:** raise chorus lift, adjust LUFS and energy to match lane targets.
- **Writer‑room iteration:** compare versions; keep the one that climbs on the weak axis.
- **Post‑release debrief:** backtest outcomes; refine lane profiles and creative rubrics.

## Governance & inputs

- Audio features come from a local **Automator** extractor (no audio leaves your machine in local mode).
- Cultural inputs can be curated or evaluator‑proxied; lyrics are **licensed/creator‑provided** when used.
- Methods are documented in the technical whitepaper; weights/archetypes remain proprietary but **auditable at the axis level**.

## Ownership & IP (short)

© 2025 **Bellweather Studios / Keith Hetrick**. The taxonomy, normalization design, archetype construction, and market‑tier calibration are proprietary. Code languages, standard DSP/NLP primitives, and public standards are generic.

## FAQ

**Is HCI “taste”?** No. It’s an explicit measurement of six well‑defined areas that correlate with historical and current success patterns.

**Will lyrics be fully analyzed?** Yes—via the Luminaire HLM/HLI modules with licensed or user‑provided text.

**Can I use this outside pop?** Yes—profiles are market/lane‑specific (e.g., US_Pop_2025).

## Contact

Bellweather Studios / Keith Hetrick — inquiries via existing partner channels.
