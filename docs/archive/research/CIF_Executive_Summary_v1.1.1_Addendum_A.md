# CIF — Executive Summary (Plain-English, 2 pages)

> Companion to v1.1.1 + Addendum A. Same logic as the technical paper, distilled for non-technical readers.

## Page 1

### What this is

A neutral, auditable way to **profile a song** and compute one balanced index: the **Hit Confidence Index (HCI)** in \([0,1]\). HCI averages six balanced views (axes): **Market, Sonic, Emotional, Historical (Echo/Novelty), Cultural, Creative**.

### How it’s computed (plain English)

1. We standardize objective features (tempo, loudness, structure, etc.).
2. We tame extremes and map each feature to a 0–1 scale.
3. We average related features into six **axes**.
4. We average the axes into **HCI**, with fairness guardrails so no single axis dominates.
5. The **Historical Echo** term checks similarity to proven patterns while still rewarding tasteful novelty.

### What HCI is not

- Not a prediction of success or a guarantee.
- Not tuned to any individual or demographic.
- Not using lyrics for scoring yet (lyrics are advisory-only for now).

### Safeguards & quality

- **Goldilocks caps** prevent any one axis from overpowering HCI.
- If a feature can’t be measured (e.g., no reliable chorus), we **exclude it** for that song—no guesswork.
- We run **repeatability** and **confidence** checks to ensure stability.

## Page 2

### Figure 1. CIF Pipeline (schematic)

Automator (features) → Feature standardization → Per-feature 0–1 mapping → **Six axes** → **HCI**  
_Callout: “Resonance Principle” = echo of proven patterns + room for tasteful novelty._

### How to read HCI (descriptive bands)

| Band      | Typical interpretation                      |
| --------- | ------------------------------------------- |
| 0.80–1.00 | Extremely strong multi-axis balance; rare.  |
| 0.70–0.79 | Strong balance with minor refinement areas. |
| 0.60–0.69 | Solid; likely needs targeted improvements.  |
| 0.50–0.59 | Mixed; address weakest axes first.          |
| < 0.50    | Early-stage; focus on fundamentals.         |

_(Bands are descriptive, not thresholds or guarantees.)_

### Glossary (selected)

- **HCI:** One index (0–1) summarizing six axes.
- **Axis:** A focused view (e.g., “Market”) built from related features.
- **Historical Echo (HEM):** How tastefully the song echoes proven patterns and balances novelty.
- **Trend Guardrails (Goldilocks caps):** Limits that keep the score fair and balanced.
- **TTC:** Time-to-Chorus (seconds).
- **Chorus-lift:** Loudness lift from verse to chorus (dB).
- **Profile:** The region/style context (e.g., US Pop 2025) that sets norms.
- **Bootstrap CI:** A way to express statistical confidence in the score.
- **Proxy (lyric):** Temporary lyric-like hints used outside scoring until the lyric engine is mature.
- **Run Card:** A one-page record that lets you reproduce a result.

### Roadmap (what’s next)

- **Lyrics** move from advisory to their **own axis** after validation.
- As that happens, old lyric proxies are **phased out** on a published schedule.
- Ongoing transparency: reproducible figures, open auditing of assumptions.

---

**Note:** This summary is not a marketing document. It is a **plain-English companion** to an auditable technical specification.
