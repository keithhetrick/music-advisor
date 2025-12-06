# Music Advisor — Integration Guide (Trend Snapshots · Router · Norms)

**Last Updated:** 2025-10-30

## Directory Layout (install the host once via outer venv)

```bash
pip install --no-build-isolation -e vendor/MusicAdvisor_BuilderPack/builder/export/MusicAdvisor
```

\```
MusicAdvisor/
Router/
Router_AutoloadTrendSnapshots.patch.yaml
Knowledge/
TrendSnapshots/
manifest.yaml
2025/
TrendSnapshot_v2025_Billboard_Macro_Shift.yaml # canonical
Notes/ # optional: human notes
\_archive/ # old snapshots
norms/
2025/
streaming.json
radio.json
tiktok.json
schemas/
datapack.schema.json # optional (reference/lint only)
tools/
validate_datapack.py
\```

---

## 1) Place Files

- Trend snapshot → `Knowledge/TrendSnapshots/2025/`
- Manifest → `Knowledge/TrendSnapshots/manifest.yaml`
- Router patch → `Router/Router_AutoloadTrendSnapshots.patch.yaml`
- Norms → `norms/2025/`
- Schema → `schemas/datapack.schema.json` _(optional)_

### Zip hygiene

\```bash
zip -r MusicAdvisor*clean.zip MusicAdvisor -x "*/\_\_MACOSX/\_" "\*/.DS_Store"
\```

---

## 2) Router Patch Behavior

- Auto-loads snapshots on `/advisor ingest`
- Recursively scans `Knowledge/TrendSnapshots/**/*.(yaml|json)`
- Loads the latest version per `id`
- Provides trend context into Market / Sonic / Cultural layers

---

## 3) Trend Snapshot Naming & Versioning

**Filename format**
\```
TrendSnapshot_vYYYY_BriefTitle.yaml
\```

### Inside file

- `id` (stable)
- `version` (`YYYY.MM.DD`)
- `generated_at` (ISO8601)
- optional `valid_until`

**One canonical YAML per snapshot `id`**

- Move `.json` / `.md` versions → `Notes/` or `_archive/` if needed

---

## 4) Historical Echo Rule

\```
40y = 0.50  
30y = 0.20  
20y = 0.20  
10y = 0.10
\```

Flag if all echoes `< 0.35` → weak historical resonance.

---

## 5) Market Signal Priorities

- Paid streams > ad-supported > programmed
- Use paid-tier weighting in Hit Confidence Index

---

## 6) Schema vs Runtime Checks

- `schemas/datapack.schema.json` = **reference & optional lint**
- **Runtime source of truth = inline validation rules**
- If mismatch: update schema to match inline rules

---

## 7) Quick Usage

\```
/cp start
/cp edit region=US
/cp edit genre=Pop
/cp edit MARKET_NORMS.profile=US_Pop_2025
/cp finalize
/advisor ingest
/advisor run full
/advisor export summary
\```

Expected in runs: Baseline block present, HCI_v1 returned, trend snapshots applied from `Knowledge/TrendSnapshots`, norms pulled from `norms/<year>/`. If HCI or Baseline is missing, verify file placement above.

---

## Integration Steps

Minimal Flow
/audio import {...}
/audio map pack region=US profile=US_Pop_2025
/audio finalize → /advisor ingest → /advisor run full
/advisor export summary
/baseline status # optional visibility

JSON export shape (excerpt)
{
"generated_at": "...",
"region": "US",
"Baseline": {
"active_profile": "US_Pop_2025",
"effective_utc": "2025-11-01T00:00:00Z",
"previous_profile": "US_Pop_2024Q4",
"pinned": false,
"note": "HCI_v1 model unchanged; MARKET_NORMS refreshed."
}
}

## 8) Maintenance

- Keep `_archive/` out of active ingest
- Commit snapshots with dates + CHANGELOG if updating frequently
