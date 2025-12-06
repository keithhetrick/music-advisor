# MusicAdvisor — Tier 2 Workflow (client + Codex)

This doc explains how to develop **Modern Tier 2** of the Historical Spine using **two agents in parallel**:

- **Client (browser)** → Architect / reviewer / explainer.
- **Codex (VS Code)** → Repo mechanic / implementer.

This keeps `music-advisor` clean, and Tier 1 behavior stable, while we add Tier 2.

---

## 0. Roles at a Glance

### Client (Music Advisor — Tier 2 Co-Architect)

- Lives in the browser as a custom client experience with a Tier 2 meta-prompt.
- Knows _design_ and _intent_:
  - How tiers relate (Tier 1 vs Tier 2 vs Deep/Vintage).
  - What `TIER2_PLAN.md` is trying to achieve.
  - How `historical_echo_v1` should be interpreted.
- Works ONLY from:
  - Code and text you paste into chat.
  - CLI output you paste into chat.
- Never touches the repo directly.

### Codex (Music Advisor — Tier 2 Implementation Assistant)

- Runs inside VS Code on the local `music-advisor` repo.
- Knows the **file tree** and can:
  - Open / edit Python scripts.
  - Suggest new scripts.
  - Propose CLI commands to run in the terminal.
- Must treat:
  - Tier 1 as **frozen behavior**.
  - `TIER2_PLAN.md` as the **source of truth** for Tier 2.

---

## 1. What Tier 2 Is (Quick Definition)

- **Tier 1 (existing):**

  - `EchoTier_1_YearEnd_Top40_Modern`
  - Billboard **Year-End Hot 100 Top 40**, years **1985–2024**.
  - Implemented in:
    - `data/spine/spine_core_tracks_v1.csv`
    - `data/spine/spine_master_v1_lanes.csv`
    - `spine_master_v1_lanes` table inside `data/historical_echo/historical_echo.db`
    - `tools/hci_echo_probe_from_spine_v1.py`
    - `historical_echo_v1` overlay into `.hci.json` and `.client.rich.txt`

- **Tier 2 (new):**
  - `EchoTier_2_YearEnd_Top100_Modern`
  - Billboard **Year-End Hot 100 Top 100** (ranks 1–100), years **1985–2024**.
  - Purpose:
    - Add more **modern hit surface** (Top 100 instead of only Top 40).
    - Tier 2 is an **optional neighbor pool**, NOT a new HCI baseline.
    - HCI_v1 stays anchored to Tier 1.

---

## 2. Files Driving Tier 2 Work

- **Plan / Spec:**
  - `TIER2_PLAN.md` (in repo root or `docs/`):
    - Precise goals.
    - Target CSV / table names.
    - Steps 1–6 for implementation.
- **Core Tier 1 references (read-only for Tier 2 dev):**
  - `data/spine/spine_core_tracks_v1.csv`
  - `data/spine/spine_master_v1_lanes.csv`
  - `data/historical_echo/historical_echo.db`
  - `tools/hci_echo_probe_from_spine_v1.py`
  - `scripts/ma_hci_builder.sh`

---

## 3. Day-to-Day Workflow (Human Loop)

You work in a loop:

1. **Ask the client (browser) for design / next steps**

   - Example:
     - “Given this CLI output, what should I have Codex do next for Tier 2?”
     - “Does this new `hci_echo_probe_from_spine_v1.py` still keep Tier 1 behavior stable?”

2. **Ask Codex (VS Code) to implement**

   - Open `TIER2_PLAN.md`.
   - Give a kick-off prompt, e.g.:

     > “Act as the _Music Advisor — Tier 2 Implementation Assistant_. Read `TIER2_PLAN.md` and implement **Step 1 (Tier 2 core CSV)** exactly as described, without changing any Tier 1 files or HCI logic. Show me the new script(s) and CLI command(s) to build `spine_core_tracks_tier2_modern_v1.csv`.”

   - Let Codex:
     - Propose new scripts under `tools/spine/`.
     - Suggest exact CLI commands.

3. **Run commands locally**

   - In the terminal, run the commands Codex suggests.
   - If there are errors:
     - Copy-paste the full error back into Codex first.

- If design questions arise, paste into the client.

4. **Paste CLI output into the client for interpretation**

   - Example:
     - Coverage stats from SQLite.
     - Backfill logs (“Still missing audio: ###”).

- Client’s job:
  - Sanity-check results.
  - Decide whether it’s “good enough” or if Tier 2 needs more sources / fixes.
  - Suggest the _next_ step for Codex.

5. **Repeat**
   - Move through `TIER2_PLAN.md` steps:
     - Step 1: core CSV.
     - Step 2: audio enrichment.
     - Step 3: master + lanes CSVs.
     - Step 4: import into DB.
     - Step 5: extend echo probe (`--tiers`).
     - Step 6: diagnostics and sanity checks.

---

## 4. What Must NOT Break

While doing Tier 2 work:

- Tier 1 must remain stable:
  - `spine_master_v1_lanes` table.
  - `spine_core_tracks_v1.csv`.
  - HCI_v1 calibration and semantics.
- Existing flows (like `scripts/ma_hci_builder.sh`) must:
  - Keep using Tier 1 by default for `historical_echo_v1`.
  - Continue working even if Tier 2 is not fully built.

If any proposed change from Codex risks that, ask the client:

- “Will this change affect Tier 1 behavior?”
- “Is this still backward compatible?”

---

## 5. How to Test Tier 2 Once It’s Wired

When Tier 2 is implemented:

1. **Check DB counts**

   - Use `sqlite3 data/historical_echo/historical_echo.db` to confirm:
     - `spine_master_tier2_modern_lanes_v1` exists.
     - Row count ≈ 4000 (40 years × 100 ranks) if Year-End data is complete.
     - Reasonable `has_audio` coverage.

2. **Probe with Tier 1 only (baseline)**

   - Run `hci_echo_probe_from_spine_v1.py` on a WIP with default settings (Tier 1 only).
   - Confirm output matches previous Tier 1 behavior.

3. **Probe with Tier 1 + Tier 2**

   - Run the same WIP with something like:
     - `--tiers tier1_modern,tier2_modern`
   - Confirm:
     - Neighbors now include some Top 41–100 songs.
     - No crashes or weird schema issues.
     - The results still feel musically sane.

4. **Ask the client to interpret**

- Paste the Tier 1-only vs Tier 1+2 neighbor lists into the client.
- Use the client to:
  - Explain how Tier 2 changed the echo landscape.
  - Decide whether Tier 2 should become part of any default modes later.

---

## 6. Mental Model Summary

- **Client** = “What should we build? Does this look right?”
- **Codex** = “Here’s the code and commands to do it.”
- **You** = the conductor:
  - Trigger Codex to implement plan steps.
- Paste outputs back into the client for interpretation and sign-off.
  - Keep Tier 1 sacred while you grow Tier 2.

Once Tier 2 is solid, the same pattern can be used later for Deep Echo and Vintage tiers.
