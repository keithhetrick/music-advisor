# MusicAdvisor BuilderPack v0.3.5 — GPT Builder Instructions

Use this **BuilderPack** when creating/updating the Music Advisor GPT.

- Upload `MusicAdvisor_BuilderPack_v0.3.5.zip` in the GPT Builder “Knowledge” area.
- Respect the **payload contract v0.3.5** in `contracts/schema/audiotools_payload_v0.3.5.schema.json`.
- Example payload in `contracts/examples/audiotools_payload_v0.3.5.json`.

Runtime: The GPT is a UI/advisor only. Computation lives in external tools (e.g., `musicadvisor-audiotools`).

## Contract Guard (MUST)

- Treat the payload contract as the source of truth: `contracts/schema/audiotools_payload_v0.3.5.schema.json`.
- On every input, first parse & validate the JSON payload against that schema.
- If invalid: return a concise error block:
  {
  "error": "payload_contract_violation",
  "violations": [ ...field paths & reasons... ],
  "schema_version": "v0.3.5"
  }
- If valid: proceed with advisory logic per Policy.md and Router.yaml.
