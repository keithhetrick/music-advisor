# 🎧 MusicAdvisor — Trend Snapshot Guide (v1.1)

## Purpose

**Trend Snapshots** keep the MusicAdvisor aware of the _current music ecosystem_ while the **HCI Framework** handles timeless hit DNA.

- **HCI** = emotional + structural universals (decades of hits already known)
- **Snapshot** = current-market calibration (3–4 month window)

> ✨ Snapshots do NOT score — they update _advice on modern execution._

---

## 🧠 What the Snapshot Tracks

- Intro length / TTC (Time-To-Chorus)
- Hook cadence & entry timing
- Section ratios (V:P:C structure)
- Tempo & rhythm norms
- Harmonic warmth vs tension
- Vocal textures (dry/air/crack/hiss)
- Acoustic vs synthetic balance
- Archetype & cultural momentum patterns

---

## 🎵 What Songs to Feed the Snapshot

| Category                   | Why                             | Weekly |
| -------------------------- | ------------------------------- | ------ |
| Current hits               | anchors market pulse            | 5–10   |
| Rising emotional/folk acts | detects emerging wave           | 3–6    |
| Your WIPs                  | tunes to your artistic identity | 2–5    |
| TikTok breakout ballads    | early signals                   | 1–3    |

> ❌ Do **not** feed 30–40-year-old history — HCI already knows it.

📌 **Feed the "now" that matches your lane.**

---

## 🎶 Starter Reference List (Folk-Pop • Emotional • Soulful)

### Core Modern Lane

- Noah Kahan — Stick Season
- Zach Bryan — I Remember Everything
- Teddy Swims — Lose Control
- Tyler Childers — Lady May
- Hozier — Too Sweet
- Leon Bridges — Beyond
- Caamp — By and By
- Kacey Musgraves — Deeper Well

### Soul / Organic Modern

- Allen Stone — Consider Me
- Yebba — Evergreen
- Daniel Caesar — Always
- Jon Batiste — Butterfly

### Pop-format Updates

- Olivia Rodrigo — vampire
- Tate McRae — greedy
- Chappell Roan — HOT TO GO!

### Indie / TikTok Emotional

- Lizzy McAlpine — ceilings
- Holly Humberstone — Into Your Room
- Gracie Abrams — I miss you, I'm sorry

---

## 🔗 Enable Snapshot Reference System

```bash
/reference enable
/reference set mode=curated
/reference set window_days=120
/reference guidance="Modern Folk-Pop Emotional Crossover"
```

---

## ➕ Add Tracks Manually

```bash
/reference add track="Noah Kahan - Stick Season"
```

### Add Spotify URLs

```bash
/reference add url=https://open.spotify.com/track/<id>
```

### Batch Mode

```bash
/reference start batch
/reference add url=...
/reference add url=...
/reference add url=...
/reference commit tag="FolkPopPulse_2025_11_A"

or

/reference start batch
/reference add url=https://open.spotify.com/track/<id>
/reference add track="Artist - Title"
/reference commit tag="WeeklyPulse_2025_11_01"
```

### Convert to Trend Snapshot Input

```bash
/trend integrate references tag="FolkPopPulse_2025_11_A"
```

---

## 🕒 Weekly Auto-Refresh (Safe Mode)

> Evolves taste slowly. No drift. Preserves HCI stability.

```bash
/trend policy set auto_refresh=true
/trend policy set cadence=weekly
/trend policy set source=warehouse
/trend policy set window_days=90
/trend policy set min_tracks=10
/trend policy set ratio=70:30
/trend policy set protect_hci=true
/trend policy set label="FolkPop_2025_Core"
```

### What it runs automatically

```bash
/trend rollup from=warehouse window=90
/trend snapshot merge base=LATEST delta=ROLLUP ratio=70:30
/trend snapshot finalize name=TREND_<today> source=auto
/datahub reload
```

---

## 🧪 Monthly Manual Pulse

```bash
/reference commit tag="MonthlyPulse_2025_11"
/trend integrate references tag="MonthlyPulse_2025_11"
/trend snapshot finalize name=TREND_2025_11_01 source=manual
/datahub reload
```

---

## 🧭 Architecture

### Two Brains Working Together

| Layer              | Role                                | Data           |
| ------------------ | ----------------------------------- | -------------- |
| **HCI**            | timeless resonance & hit psychology | internal       |
| **Trend Snapshot** | recency calibration & format        | curated + WIPs |

✅ HCI stays fixed
✅ Snapshot evolves
✅ Advice modernizes
✅ Scoring remains stable

---

## ✅ Routine Summary

### Weekly

- Add new hits (5–10)
- Add rising emotional folk voices (3–6)
- Add your WIPs (2–5)
- Let automation update snapshot

### Monthly

- Commit + tag curated batch
- Reload snapshot

---

## 🗣 Plain-English Version

You already have the intelligence of decades of hits (HCI*v1).
Trend Snapshots teach the Advisor what the \_world sounds like today* and what **you** care about musically.

This builds:

> **A living taste graph trained by your ear + current culture.**

---

## 🚀 First Activation Command

```bash
/reference enable
/reference set mode=curated
/reference set window_days=120
/reference guidance="Modern Folk-Pop Emotional Crossover"
```

Paste Spotify URLs right after to begin feeding the engine 🎧🔥

```bash

```
